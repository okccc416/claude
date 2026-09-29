"""本地小模型兜底：用假模型验证触发条件、防编造规则与结论上限；用本地假服务验证两种接口格式。"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from avmvp import ReferenceDB, Validator
from avmvp.llm_fallback import LLMAssistedValidator, LocalLLM, guard
from avmvp.validator import ACCEPT, CONFIRM, FIX

FIXTURE = Path(__file__).parent / "fixture_reference.csv"
EMPTY = {"block": "", "street": "", "unit": "", "postal_code": "", "building": "", "recipient": "", "phone": "",
         "notes": "", "is_complete_address": False}


class FakeLLM:
    def __init__(self, answer=None, error=None):
        self.answer, self.error, self.calls = answer, error, []

    def extract(self, text):
        self.calls.append(text)
        if self.error:
            raise self.error
        return {**EMPTY, **(self.answer or {})}


@pytest.fixture(scope="module")
def base():
    return Validator(ReferenceDB.load(FIXTURE))


def test_not_called_when_rules_are_confident(base):
    llm = FakeLLM({"block": "1", "street": "Raffles Place"})
    v = LLMAssistedValidator(base, llm)
    assert v.validate("10 Bayfront Avenue, Singapore 018956").action == ACCEPT
    assert llm.calls == []


def test_rescues_badly_misspelled_street_but_only_confirms(base):
    # 规则救不回来的两处拼错；模型纠正了路名，但改写过内容 -> 只能 CONFIRM
    assert base.validate("34A Pxxle Rxd").action == FIX
    v = LLMAssistedValidator(base, FakeLLM({"block": "34A", "street": "Poole Road", "is_complete_address": True}))
    res = v.validate("34A Pxxle Rxd")
    assert res.action == CONFIRM
    assert (res.entity.blk, res.entity.road) == ("34A", "POOLE ROAD")
    assert "LLM_ASSISTED_PARSE" in res.reasons


def test_hallucinated_numbers_are_dropped(base):
    # 输入里没有 10 和 018956：模型"补"出来的楼栋号和邮编必须被丢弃，不能把不存在的地址洗成存在
    v = LLMAssistedValidator(base, FakeLLM({"block": "10", "street": "Bayfront Avenue", "postal_code": "018956"}))
    assert v.validate("999 Bayfront Avenue").action == FIX


def test_guard_uses_whole_digit_runs():
    raw = "Pls call 91234567, Tampines Avenue"
    assert guard({**EMPTY, "block": "12", "postal_code": "912345"}, raw)["block"] == ""
    assert guard({**EMPTY, "postal_code": "912345"}, raw)["postal_code"] == ""
    assert guard({**EMPTY, "block": "390", "unit": "#05-12"}, "Blk390 lvl 5 unit 12")["unit"] == "#05-12"
    assert guard({**EMPTY, "postal_code": "018956"}, "10 Bayfront 18956")["postal_code"] == "018956"


def test_junk_stays_rejected(base):
    v = LLMAssistedValidator(base, FakeLLM({"phone": "91234567", "notes": "same as last order"}))
    assert v.validate("same as last order 91234567").action == FIX


def test_model_failure_falls_back_to_rules(base):
    v = LLMAssistedValidator(base, FakeLLM(error=TimeoutError("local model timed out")))
    res = v.validate("34A Pxxle Rxd")
    assert res.action == FIX and v.stats.errors == 1


def test_verbatim_fields_may_accept(base):
    # 规则因无法识别的片段只给 CONFIRM；模型拆出的字段全部原样来自输入 -> 可以直接通过
    raw = "zzqx wobble 10 Bayfront Ave 018956"
    assert base.validate(raw).action == CONFIRM
    v = LLMAssistedValidator(base, FakeLLM({"block": "10", "street": "Bayfront Ave", "postal_code": "018956",
                                            "notes": "zzqx wobble"}))
    res = v.validate(raw)
    assert res.action == ACCEPT
    assert v.to_response(res)["result"]["nonAddressInfo"]["notes"] == ["zzqx wobble"]


def test_disagreement_keeps_rules_and_adds_candidate(base):
    raw = "zzqx 10 Bayfront Ave 018956"
    v = LLMAssistedValidator(base, FakeLLM({"block": "1", "street": "Raffles Place"}))
    res = v.validate(raw)
    assert (res.entity.blk, res.entity.road) == ("10", "BAYFRONT AVENUE")
    assert "LLM_ALTERNATIVE_CANDIDATE" in res.reasons


# ---------------------------------------------------------------- 接口格式（本地假服务）
class _Stub(BaseHTTPRequestHandler):
    last = {}

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _Stub.last = {"path": self.path, "body": body}
        content = json.dumps({**EMPTY, "block": "34A", "street": "Poole Road"})
        if self.path == "/api/chat":
            payload = {"message": {"role": "assistant", "content": content}, "done": True}
        else:
            payload = {"choices": [{"message": {"role": "assistant", "content": content}}]}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def stub():
    srv = HTTPServer(("127.0.0.1", 0), _Stub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.mark.parametrize("api,path", [("ollama", "/api/chat"), ("openai", "/v1/chat/completions")])
def test_local_llm_client(stub, api, path):
    out = LocalLLM(endpoint=stub, model="qwen2.5:1.5b", api=api).extract("34A Pxxle Rxd")
    assert out["block"] == "34A" and out["street"] == "Poole Road"
    req = _Stub.last
    assert req["path"] == path and req["body"]["model"] == "qwen2.5:1.5b"
    assert req["body"]["messages"][-1] == {"role": "user", "content": "34A Pxxle Rxd"}
    schema = req["body"]["format"] if api == "ollama" else req["body"]["response_format"]["json_schema"]["schema"]
    assert "postal_code" in schema["properties"]
