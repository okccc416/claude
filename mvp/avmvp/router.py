"""按国家 / 地区代码（regionCode）把请求分给对应的校验引擎。

  SG                      新加坡专用引擎（逐门牌验真 + 置信度 + 可选小模型兜底）
  AU DE FR NL             多市场引擎，A 类：官方地址表逐门牌验真
  AE SA                   多市场引擎，B 类（中东）：道路 / 楼宇 / 片区验真
  MY ID TH VN PH          多市场引擎，C 类（东南亚）：道路 / 楼宇 / 片区验真

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


class MarketRouter:
    def __init__(self, sg_factory: Callable[[], object] | None, markets: list[str], parser: str = "hybrid",
                 log=print):
        self.sg_factory = sg_factory
        self.parser = parser
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
                    self._engines[code] = Engine(code, parser)
                self.log(f"已加载 {code} 校验引擎（{time.time() - t:.1f}s）")
        return self._engines[code]

    def preload(self) -> None:
        for c in self.codes:
            if self.available(c):
                self.engine(c)

    def validate(self, code: str, text: str, strictness: str = "BALANCED") -> dict:
        code = (code or "SG").upper()
        eng = self.engine(code)
        with self._locks[code]:
            res = eng.validate(text, strictness=strictness)
            out = eng.to_response(res)
        if code == "SG":
            out["result"].setdefault("metadata", None)
            out["result"]["metadata"] = {**(out["result"]["metadata"] or {}), "regionCode": "SG",
                                         "marketClass": "A", "parser": "rules"}
        return out
