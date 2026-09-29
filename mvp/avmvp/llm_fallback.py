"""本地小模型兜底：规则处理不好的输入，交给本地部署的小模型（如 Qwen）拆字段，再回到参考库裁决。

分工原则："AI 负责读懂，参考库负责裁决"
- 只在规则结果不理想时调用（查不到 / 有歧义 / 有无法解析的片段），不进常规热路径
- 模型只输出结构化字段，不决定地址真假；拆出的字段重新走同一套参考库比对和结论规则
- 防编造：楼栋号、单元号、邮编必须在原始输入里真实出现过，否则丢弃
- 模型改写过的内容（如纠正了路名）最多给 CONFIRM；只有字段全部原样来自输入时才允许 ACCEPT
- 任何异常或超时都退回规则结果，不影响可用性

支持两种本地服务接口（均为标准库实现，无额外依赖）：
- Ollama：        POST {endpoint}/api/chat，format 传 JSON Schema
- OpenAI 兼容：   POST {endpoint}/v1/chat/completions，response_format 传 json_schema
                  （llama.cpp server、vLLM、LM Studio 等均提供此接口）
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from dataclasses import dataclass, field, replace

from .noise import NoiseResult
from .normalize import match_key
from .validator import ACCEPT, CONFIRM, FIX, Result, Validator

FIELDS = ["block", "street", "unit", "postal_code", "building", "recipient", "phone", "notes"]

SCHEMA = {
    "type": "object",
    "properties": {**{k: {"type": "string"} for k in FIELDS}, "is_complete_address": {"type": "boolean"}},
    "required": [*FIELDS, "is_complete_address"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You extract Singapore address fields from messy order text written by customers.
Return JSON only, matching the schema. Rules:
- Copy block number, unit and postal code exactly as they appear in the input. If one is not in the input, return "". Never guess them.
- street: the street name. Expand abbreviations (Ave -> Avenue, AMK -> Ang Mo Kio) and fix obvious spelling mistakes.
- unit: format as #FF-UUU when floor and unit are given (e.g. "Level 5 Unit 12" -> "#05-12").
- building: a building, estate or place name if present, else "".
- recipient / phone / notes: people or company names, phone numbers, and delivery instructions. Never put them in address fields.
- is_complete_address: true only if the input contains enough to identify one specific building."""

FEW_SHOT = [
    ("Attn: Jason Teo, Blk123 AMK Ave3 #05-12 S(560123) pls call b4 delivery 91234567",
     {"block": "123", "street": "Ang Mo Kio Avenue 3", "unit": "#05-12", "postal_code": "560123", "building": "",
      "recipient": "Jason Teo", "phone": "91234567", "notes": "pls call b4 delivery", "is_complete_address": True}),
    ("same as last order, call me 81234567",
     {"block": "", "street": "", "unit": "", "postal_code": "", "building": "", "recipient": "",
      "phone": "81234567", "notes": "same as last order, call me", "is_complete_address": False}),
    ("24 Lilak Wlak",
     {"block": "24", "street": "Lilac Walk", "unit": "", "postal_code": "", "building": "", "recipient": "",
      "phone": "", "notes": "", "is_complete_address": True}),
]

# 规则结果里的这些原因码说明"没读懂"，值得请模型再看一眼
TRIGGER_FIX_REASONS = {"NO_MATCH", "AMBIGUOUS_MULTIPLE_CANDIDATES", "POSTCODE_STREET_MISMATCH"}


def should_trigger(res: Result) -> bool:
    if res.action == FIX:
        return bool(TRIGGER_FIX_REASONS & set(res.reasons))
    return "UNRESOLVED_TOKENS" in res.reasons


@dataclass
class LocalLLM:
    """本地模型客户端。api = "ollama" 或 "openai"（OpenAI 兼容接口）。"""
    endpoint: str = "http://127.0.0.1:11434"
    model: str = "qwen2.5:1.5b"
    api: str = "ollama"
    timeout: float = 20.0

    def _messages(self, text: str) -> list[dict]:
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        for q, a in FEW_SHOT:
            msgs += [{"role": "user", "content": q}, {"role": "assistant", "content": json.dumps(a)}]
        msgs.append({"role": "user", "content": text})
        return msgs

    def extract(self, text: str) -> dict:
        if self.api == "ollama":
            url = self.endpoint.rstrip("/") + "/api/chat"
            body = {"model": self.model, "messages": self._messages(text), "stream": False,
                    "format": SCHEMA, "options": {"temperature": 0}}
        else:
            url = self.endpoint.rstrip("/") + "/v1/chat/completions"
            body = {"model": self.model, "messages": self._messages(text), "temperature": 0,
                    "response_format": {"type": "json_schema",
                                        "json_schema": {"name": "address_fields", "schema": SCHEMA, "strict": True}}}
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())
        content = data["message"]["content"] if self.api == "ollama" else data["choices"][0]["message"]["content"]
        out = json.loads(content)
        return {k: (out.get(k) or "") if k != "is_complete_address" else bool(out.get(k)) for k in SCHEMA["properties"]}


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def guard(fields: dict, raw: str) -> dict:
    """防编造：楼栋号 / 单元号 / 邮编里的数字必须与输入中某一段完整数字一致，否则清空。

    按"完整数字段"比较而不是子串，避免模型编出的 12 恰好是电话 91234567 的一部分而蒙混过关。
    """
    runs = set(re.findall(r"\d+", raw or ""))
    stripped = {r.lstrip("0") for r in runs}
    f = dict(fields)
    postal = _digits(f.get("postal_code", ""))
    if postal and not (len(postal) == 6 and (postal in runs or (postal[0] == "0" and postal[1:] in runs))):
        f["postal_code"] = ""
    if f.get("block") and _digits(f["block"]) not in runs:
        f["block"] = ""
    unit_nums = [n.lstrip("0") for n in re.findall(r"\d+", f.get("unit", "")) if n.lstrip("0")]
    if f.get("unit") and (not unit_nums or not all(n in stripped for n in unit_nums)):
        f["unit"] = ""
    return f


def verbatim(fields: dict, raw: str) -> bool:
    """地址字段是否都能在原始输入里原样找到（规范化后比较）。"""
    key = f" {match_key(raw)} "
    for k in ("block", "street", "postal_code"):
        v = fields.get(k)
        if v and f" {match_key(v)} " not in key:
            return False
    return True


def compose(fields: dict) -> str:
    parts = []
    head = " ".join(x for x in (fields.get("block"), fields.get("street")) if x)
    if head:
        parts.append(head)
    if fields.get("unit"):
        parts.append(fields["unit"])
    if fields.get("building") and not (fields.get("block") and fields.get("street")):
        parts.append(fields["building"])
    if fields.get("postal_code"):
        parts.append(f"Singapore {fields['postal_code']}")
    return ", ".join(parts)


@dataclass
class FallbackStats:
    calls: int = 0
    errors: int = 0
    used: int = 0
    latency_ms: list[float] = field(default_factory=list)


class LLMAssistedValidator:
    """在规则校验器外面包一层：规则处理不好时才调用本地模型。"""

    def __init__(self, validator: Validator, llm, trigger=should_trigger):
        self.v, self.llm, self.trigger = validator, llm, trigger
        self.db = validator.db
        self.stats = FallbackStats()

    def to_response(self, res: Result) -> dict:
        return self.v.to_response(res)

    def validate(self, raw: str, strictness: str | None = None) -> Result:
        res = self.v.validate(raw, strictness=strictness)
        if not self.trigger(res):
            return res
        self.stats.calls += 1
        t = time.perf_counter()
        try:
            fields = guard(self.llm.extract(raw), raw)
        except Exception:  # 本地服务不可用 / 超时 / 输出不是合法 JSON：一律退回规则结果
            self.stats.errors += 1
            return res
        finally:
            self.stats.latency_ms.append((time.perf_counter() - t) * 1000)
        text = compose(fields)
        if not text:
            return res
        res2 = self.v.validate(text, strictness=strictness)
        if res2.action == FIX or res2.entity is None:
            return res
        if res.entity is not None and res2.entity.eid != res.entity.eid:
            # 规则和模型给出不同地址：不替用户做选择，保留规则结论，把模型的建议放进候选
            res.candidates = [res2.entity.eid, *res.candidates]
            res.reasons.append("LLM_ALTERNATIVE_CANDIDATE")
            return res
        if res.entity is not None and res.action == ACCEPT:
            return res
        noise = res.noise or NoiseResult(text="")
        for key, bucket in (("phone", noise.phones), ("recipient", noise.recipients), ("notes", noise.notes)):
            if fields.get(key) and all(fields[key] not in x and x not in fields[key] for x in bucket):
                bucket.append(fields[key])
        out = replace(res2, reasons=[*res2.reasons, "LLM_ASSISTED_PARSE"],
                      noise=noise if noise.removed_any else None)
        if out.action == ACCEPT and not verbatim(fields, raw):
            out.action = CONFIRM  # 模型改写过地址内容：必须请用户确认
        self.stats.used += 1
        return out
