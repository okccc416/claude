"""本地小模型解析器（多市场）：让本地部署的开源模型（Qwen 等）把地址拆成字段，再回到参考库裁决。

与新加坡的兜底（avmvp/llm_fallback.py，见 docs/08）同一原则："AI 负责读懂，参考库负责裁决"
- 模型只输出字段（门牌 / 单元 / 楼名 / 道路 / 片区 / 邮编），不判断地址真假
- 防编造：门牌、单元、邮编里的数字必须在原文里出现过；道路 / 楼名 / 片区至少要与原文有一个词对得上，否则丢弃
- 级联：只在规则 + 机器学习拿不准（没有直接通过）时才调用；模型改写过的字段（不是原文照抄）最多给 CONFIRM
- 任何异常、超时都退回原结果

两种后端：
- LlamaCppLLM：进程内运行 GGUF 模型（llama-cpp-python，纯 CPU 可用），用 JSON Schema 约束输出
- HTTPLLM：OpenAI 兼容接口（llama.cpp server、vLLM、Ollama 的 /v1 等），生产部署用
"""

from __future__ import annotations

import json
import re
import time
import urllib.request

from rapidfuzz import fuzz

from .markets import MARKETS
from .parse import HOUSE_NO, Parsed, Span, generic_name, strip_noise
from .reference import MarketReference
from .text import core_key, fold, key, norm_postcode, skeleton

FIELDS = ["house_number", "unit", "building", "street", "area", "postcode"]
COUNTRY = {"AU": "Australia", "DE": "Germany", "FR": "France", "NL": "the Netherlands", "AE": "the UAE (Dubai)",
           "SA": "Saudi Arabia (Riyadh)", "MY": "Malaysia", "ID": "Indonesia", "TH": "Thailand", "VN": "Vietnam",
           "PH": "the Philippines", "CA": "Canada (Toronto)", "MX": "Mexico (Mexico City)", "PR": "Puerto Rico",
           "BR": "Brazil (São Paulo)", "AR": "Argentina (Buenos Aires)", "CL": "Chile (Santiago)",
           "CO": "Colombia (Bogotá)", "GB": "the United Kingdom (London)", "IE": "Ireland (Dublin)",
           "BE": "Belgium (Brussels)", "LU": "Luxembourg", "CH": "Switzerland (Zürich)", "AT": "Austria (Vienna)",
           "IT": "Italy (Milan)", "ES": "Spain (Madrid)", "PT": "Portugal (Lisbon)", "DK": "Denmark (Copenhagen)",
           "SE": "Sweden (Stockholm)", "NO": "Norway (Oslo)", "FI": "Finland (Helsinki)", "EE": "Estonia (Tallinn)",
           "LV": "Latvia (Riga)", "LT": "Lithuania (Vilnius)", "PL": "Poland (Warsaw)", "CZ": "Czechia (Prague)",
           "SK": "Slovakia (Bratislava)", "HU": "Hungary (Budapest)", "SI": "Slovenia (Ljubljana)",
           "HR": "Croatia (Zagreb)", "BG": "Bulgaria (Sofia)", "NZ": "New Zealand (Auckland)", "JP": "Japan (Tokyo)",
           "IN": "India (Mumbai)"}
SCHEMA = {"type": "object", "properties": {k: {"type": "string"} for k in FIELDS}, "required": FIELDS,
          "additionalProperties": False}

SYSTEM = """You split a customer-typed address from {country} into fields. Return JSON only.
- house_number: the house / building / lot number exactly as written (e.g. "12", "112/55", "21-22"), else "".
- unit: floor / unit / office / shop / villa designation exactly as written (e.g. "Level 3", "Unit 5", "Shop L2"), else "".
- building: a building, tower, mall, hotel, compound or landmark name, else "".
- street: the street / road / soi / jalan name WITHOUT the house number, as written but with abbreviations expanded
  (St -> Street, Rd -> Road, Jl -> Jalan, Jln -> Jalan, Đ. -> Đường, ถ. -> ถนน). Keep the original language and script.
- area: the neighbourhood / district / suburb (not the city or country), else "".
- postcode: the postal code exactly as written, else "".
Never invent anything that is not in the text. Company names and phone numbers are not address fields."""

FEW_SHOT = [
    ("AE", "Office 1204, Latifa Tower, Sheikh Zayed Rd, Trade Centre 1, Dubai",
     {"house_number": "", "unit": "Office 1204", "building": "Latifa Tower", "street": "Sheikh Zayed Road",
      "area": "Trade Centre 1", "postcode": ""}),
    ("ID", "Jl. Kemang Raya No.36, RT.6/RW.4, Bangka, Mampang Prpt., Jakarta Selatan 12730",
     {"house_number": "36", "unit": "", "building": "", "street": "Jalan Kemang Raya", "area": "Bangka",
      "postcode": "12730"}),
    ("TH", "539/57 ถ.เลียบทางรถไฟตลิ่งชัน แขวงบางขุนศรี เขตบางกอกน้อย กรุงเทพมหานคร 10700",
     {"house_number": "539/57", "unit": "", "building": "", "street": "ถนนเลียบทางรถไฟตลิ่งชัน", "area": "บางขุนศรี",
      "postcode": "10700"}),
]


def _messages(text: str, market: str) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM.format(country=COUNTRY.get(market, market))}]
    for _, q, a in FEW_SHOT:
        msgs += [{"role": "user", "content": q}, {"role": "assistant", "content": json.dumps(a, ensure_ascii=False)}]
    msgs.append({"role": "user", "content": text})
    return msgs


class LlamaCppLLM:
    """进程内 GGUF 模型。固定的系统提示和示例在每次调用间复用 KV 缓存，只需处理新输入。"""

    def __init__(self, model_path: str, n_threads: int | None = None, n_ctx: int = 2048):
        from llama_cpp import Llama

        import os

        self.name = model_path.rsplit("/", 1)[-1]
        # llama-cpp-python 默认只用一半的核；地址解析是单请求低延迟场景，用满全部核
        self.llm = Llama(model_path=model_path, n_ctx=n_ctx, n_threads=n_threads or os.cpu_count(), verbose=False)

    def extract(self, text: str, market: str) -> dict:
        out = self.llm.create_chat_completion(
            messages=_messages(text, market), temperature=0.0, max_tokens=160,
            response_format={"type": "json_object", "schema": SCHEMA})
        return json.loads(out["choices"][0]["message"]["content"])


class HTTPLLM:
    """OpenAI 兼容接口（llama.cpp server、vLLM、Ollama /v1 …）。"""

    def __init__(self, endpoint: str, model: str, timeout: float = 20.0):
        self.endpoint, self.name, self.timeout = endpoint.rstrip("/"), model, timeout

    def extract(self, text: str, market: str) -> dict:
        body = {"model": self.name, "messages": _messages(text, market), "temperature": 0,
                "response_format": {"type": "json_schema", "json_schema": {"name": "address", "schema": SCHEMA}}}
        req = urllib.request.Request(f"{self.endpoint}/v1/chat/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(json.loads(r.read())["choices"][0]["message"]["content"])


class CachedLLM:
    """把模型输出按（模型, 市场, 输入）缓存到 jsonl：评测重跑、错误分析不用再算一遍（CPU 上每次几秒）。"""

    def __init__(self, llm, path):
        from pathlib import Path

        self.llm, self.name, self.path = llm, llm.name, Path(path)
        self.cache: dict[str, dict] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                self.cache[r["k"]] = r["v"]

    def extract(self, text: str, market: str) -> dict:
        k = f"{self.name}|{market}|{text}"
        if k not in self.cache:
            self.cache[k] = self.llm.extract(text, market)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"k": k, "v": self.cache[k]}, ensure_ascii=False) + "\n")
        return self.cache[k]


# ---------------------------------------------------------------------------------------------- 防编造
def _digits(s: str) -> list[str]:
    return re.findall(r"\d+", fold(s))


def guard(fields: dict, raw: str, market: str) -> tuple[dict, bool]:
    """去掉原文里没有依据的字段。返回 (保留的字段, 是否全部照抄原文)。"""
    raw_f = fold(raw)
    raw_digits = set(_digits(raw))
    raw_words = set(key(raw, market).split())
    raw_skel = skeleton(raw)
    raw_compact = re.sub(r"[\W_]+", "", raw_f)
    out, verbatim = {}, True
    for k in FIELDS:
        v = str(fields.get(k) or "").strip()
        if not v:
            continue
        if k in ("house_number", "unit", "postcode"):  # 数字必须在原文里出现过
            if not set(_digits(v)) <= raw_digits:
                continue
        else:  # 名称：至少一个词对得上原文（容许拼写差异）；阿拉伯文 / 拉丁转写按辅音骨架
            # 只比较去掉类型词后的名称（"Phường Nhúm Vòng" 不能因为原文也有 Phường 就算对上）
            words = [w for w in core_key(v, market, "area" if k == "area" else "street").split() if len(w) >= 3]
            compact = re.sub(r"[\W_]+", "", fold(v))
            if words and not any(w in raw_words or any(fuzz.ratio(w, r) >= 80 for r in raw_words) for w in words) \
                    and not (len(skeleton(v)) >= 4 and skeleton(v) in raw_skel) \
                    and not (len(compact) >= 6 and fuzz.partial_ratio(compact, raw_compact) >= 85):  # 粘连写法
                continue
        out[k] = v
        if fold(v) not in raw_f:
            verbatim = False
    return out, verbatim


# ---------------------------------------------------------------------------------------------- 解析器
class LLMParser:
    name = "llm"

    def __init__(self, ref: MarketReference, llm):
        self.ref = ref
        self.llm = llm
        self.m = MARKETS[ref.market]
        self.pc_re = re.compile(self.m.postcode) if self.m.postcode else None
        self.calls = 0
        self.seconds = 0.0
        self.errors = 0

    def parse(self, raw: str) -> Parsed | None:
        text, noise, codes = strip_noise(raw)
        t = time.perf_counter()
        try:
            fields = self.llm.extract(text, self.ref.market)
        except Exception:  # noqa: BLE001 -- 模型出任何问题都退回原结果
            self.errors += 1
            return None
        finally:
            self.calls += 1
            self.seconds += time.perf_counter() - t
        fields, verbatim = guard(fields, raw, self.ref.market)
        p = Parsed(raw=raw, tokens=[], codes=codes, noise=noise, parser="llm")
        p.verbatim = verbatim  # type: ignore[attr-defined]
        p.llm_fields = fields  # type: ignore[attr-defined]
        num = fields.get("house_number", "")
        if num and HOUSE_NO.match(fold(num).replace(" ", "")):
            p.number = fold(num).replace(" ", "")
        if fields.get("unit"):
            p.unit = fold(fields["unit"])
        pc = fields.get("postcode", "")
        if pc and self.pc_re and self.pc_re.search(fold(pc)) and fold(pc).strip("0"):
            p.postcode = norm_postcode(self.pc_re.search(fold(pc)).group(0), self.ref.market)
        if fields.get("street"):
            p.streets = self._lookup(fields["street"], "street")
        if fields.get("area"):
            p.areas = self._lookup(fields["area"], "area")
        if fields.get("building") and self.ref.poi_fuzzy is not None:
            k = key(fields["building"], self.ref.market)
            for hit, score, ids in self.ref.poi_fuzzy.search(k, limit=2, min_score=88):
                if len(ids) <= 20 and not generic_name(hit):
                    p.buildings.append(Span(hit, -1, -1, ids, score, "exact" if score == 100 else "fuzzy"))
        return p

    def _lookup(self, words: str, kind: str) -> list[Span]:
        """与机器学习解析器相同的查找顺序：完整键 -> 核心键 -> 容错 -> 阿拉伯文转写骨架。"""
        ref = self.ref
        table = ref.street_keys if kind == "street" else ref.area_keys
        core = ref.street_core if kind == "street" else ref.area_core
        index = ref.street_fuzzy if kind == "street" else ref.area_fuzzy
        k = key(words, ref.market)
        if k in table:
            return [Span(k, -1, -1, sorted(table[k]), 100.0, "exact")]
        ck = core_key(words, ref.market, kind)
        if ck in core and len(ck) >= 4 and not (kind == "street" and ck in ref.area_keys):
            return [Span(ck, -1, -1, sorted(core[ck]), 97.0, "core")]
        out = []
        if index is not None and len(k) >= 4:
            for cand in {k, ck}:
                for hit, score, ids in index.search(cand, limit=2, min_score=84):
                    out.append(Span(hit, -1, -1, ids, score, "fuzzy"))
        skel = getattr(ref, "street_skel" if kind == "street" else "area_skel", None)
        if not out and skel:
            sk = skeleton(words)
            if len(sk) >= 4 and sk in skel and len(skel[sk]) <= 30:
                out.append(Span(sk, -1, -1, sorted(skel[sk]), 90.0, "translit"))
        return sorted(out, key=lambda s: -s.score)[:3]
