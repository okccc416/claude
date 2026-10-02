"""按国家 / 地区代码（regionCode）把请求分给对应的校验引擎。

  SG                      新加坡专用引擎（逐门牌验真 + 置信度 + 可选小模型兜底）
  其余 44 个市场          多市场引擎（avmvp/intl/markets.py）：
    A 类（官方地址表逐门牌验真）  AU DE FR NL CA MX BR CL CO BE LU CH AT IT ES PT DK NO FI EE LV LT PL CZ SK SI HR NZ JP
    B 类（中东）                  AE SA
    C 类（没有开放地址表）        MY ID TH VN PH GB IE SE HU BG AR IN PR
  即 Google Address Validation 覆盖的全部国家 / 地区（美国除外），外加中东和东南亚。

参考数据较大（澳洲约 600 MB），默认在第一次请求某个市场时才加载；--preload 启动时全部加载。
同一市场的请求串行执行（参考库的 SQLite 连接在线程间共享）。
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

from .intl.markets import MARKETS
from .intl.reference import DATA

ROOT = Path(__file__).resolve().parents[1]
SG = {"code": "SG", "name": "新加坡", "cls": "A", "cities": ["全岛"]}


class UnsupportedRegion(ValueError):
    pass


class LockedLLM:
    """模型实例不是线程安全的：多个市场的请求共用时串行调用。"""

    def __init__(self, llm):
        self.llm, self.name, self._lock = llm, getattr(llm, "name", "llm"), threading.Lock()

    def extract(self, text: str, market: str) -> dict:
        with self._lock:
            return self.llm.extract(text, market)


class MarketRouter:
    def __init__(self, sg_factory: Callable[[], object] | None, markets: list[str], parser: str = "hybrid",
                 log=print, llm=None, llm_markets: set[str] | None = None):
        self.sg_factory = sg_factory
        self.parser = parser
        self.llm = LockedLLM(llm) if llm is not None else None  # 可选：本地小模型兜底（多市场共用一个实例）
        self.llm_markets = llm_markets  # 开启兜底的市场（None = 全部）
        conf_path = ROOT / "models" / "confidence_intl.json"  # 多市场置信度（scripts/fit_intl_confidence.py 生成）
        if conf_path.exists():
            from .intl.confidence import IntlConfidence
            self.confidence = IntlConfidence.load(conf_path)
        else:
            self.confidence = None
        self.log = log
        self.codes = [c for c in markets if c == "SG" and sg_factory or c in MARKETS]
        self._engines: dict[str, object] = {}
        self._locks = {c: threading.Lock() for c in self.codes}
        self._load_lock = threading.Lock()

    # ------------------------------------------------------------------ 市场列表
    def available(self, code: str) -> bool:
        if code == "SG":
            return self.sg_factory is not None
        return code in MARKETS and (DATA / code / "reference.pkl").exists()

    def describe(self) -> list[dict]:
        out = []
        for c in self.codes:
            if c == "SG":
                d = dict(SG)
            else:
                m = MARKETS[c]
                d = {"code": c, "name": m.name, "cls": m.cls, "cities": [r[0] for r in m.regions]}
            d.update(available=self.available(c), loaded=c in self._engines)
            out.append(d)
        return out

    # ------------------------------------------------------------------ 引擎
    def engine(self, code: str):
        code = (code or "SG").upper()
        if code not in self.codes:
            raise UnsupportedRegion(f"不支持的 regionCode：{code}（支持：{', '.join(self.codes)}）")
        if code in self._engines:
            return self._engines[code]
        if not self.available(code):
            raise UnsupportedRegion(f"{code} 的参考数据尚未构建（见 docs/13 第 6 节）")
        with self._load_lock:
            if code not in self._engines:
                t = time.time()
                if code == "SG":
                    self._engines[code] = self.sg_factory()
                else:
                    from .intl.engine import Engine
                    parser = self.parser if (DATA / code / "crf.model").exists() else "rules"
                    use_llm = self.llm if self.llm_markets is None or code in self.llm_markets else None
                    self._engines[code] = Engine(code, parser, llm=use_llm, confidence=self.confidence)
                self.log(f"已加载 {code} 校验引擎（{time.time() - t:.1f}s）")
        return self._engines[code]

    def preload(self) -> None:
        for c in self.codes:
            if self.available(c):
                self.engine(c)

    def validate(self, code: str, text: str, strictness: str = "BALANCED", min_confidence: float | None = None) -> dict:
        code = (code or "SG").upper()
        eng = self.engine(code)
        with self._locks[code]:
            if code == "SG":  # 新加坡引擎的置信度门槛在 ConfidenceValidator 里配置
                res = eng.validate(text, strictness=strictness)
            else:
                res = eng.validate(text, strictness=strictness, min_confidence=min_confidence)
            out = eng.to_response(res)
        if code == "SG":
            out["result"].setdefault("metadata", None)
            out["result"]["metadata"] = {**(out["result"]["metadata"] or {}), "regionCode": "SG",
                                         "marketClass": "A", "parser": "rules"}
        return out
