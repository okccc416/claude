"""对照方案：用来证明"为什么不直接用更简单的做法"。

B1 模糊整串匹配（Geocoder 式）：把输入和参考库地址都当成一整串文本，取最相似的一条，
   按相似度阈值给出 ACCEPT / CONFIRM / FIX。这代表"直接复用现有地理编码 / 搜索能力"的做法。
   阈值在开发集上网格搜索，取对它最有利的一组（公平起见，宁可高估对照方案）。
B2 仅查邮编：新加坡邮编几乎一楼一码，于是"邮编查得到就通过"。这代表最朴素的本地做法。
"""

from __future__ import annotations

import numpy as np
from rapidfuzz import fuzz, process

from .normalize import match_key
from .parser import parse
from .reference import ReferenceDB
from .validator import ACCEPT, CONFIRM, FIX


class FuzzyBaseline:
    name = "B1 模糊整串匹配（Geocoder 式）"

    def __init__(self, db: ReferenceDB, t_accept: float = 95, t_confirm: float = 85):
        self.db = db
        self.choices = [match_key(f"{e.blk} {e.road} {e.postal}") for e in db.entities]
        self.t_accept, self.t_confirm = t_accept, t_confirm

    def best_matches(self, texts: list[str], chunk: int = 256) -> list[tuple[int, float]]:
        """批量取每条输入最相似的参考地址（多核）。"""
        out: list[tuple[int, float]] = []
        queries = [match_key(t) for t in texts]
        for i in range(0, len(queries), chunk):
            m = process.cdist(queries[i:i + chunk], self.choices, scorer=fuzz.token_sort_ratio,
                              dtype=np.uint8, workers=-1)
            idx = m.argmax(axis=1)
            out.extend((int(j), float(m[r, j])) for r, j in enumerate(idx))
        return out

    def decide(self, eid: int, score: float) -> tuple[str, int | None]:
        if score >= self.t_accept:
            return ACCEPT, eid
        if score >= self.t_confirm:
            return CONFIRM, eid
        return FIX, None

    def tune(self, matches: list[tuple[int, float]], expected: list[tuple[str, int | None]]) -> None:
        """在开发集上网格搜索阈值，目标：完全正确率（动作对且地址对）最高。"""
        best = (-1.0, self.t_accept, self.t_confirm)
        for ta in range(60, 101):
            for tc in range(40, ta + 1):
                ok = 0
                for (eid, s), (ea, ee) in zip(matches, expected):
                    a = ACCEPT if s >= ta else CONFIRM if s >= tc else FIX
                    ok += a == ea and (ea == FIX or eid == ee)
                if ok > best[0]:
                    best = (ok, ta, tc)
        _, self.t_accept, self.t_confirm = best


class PostalBaseline:
    name = "B2 仅查邮编"

    def __init__(self, db: ReferenceDB):
        self.db = db

    def validate(self, raw: str) -> tuple[str, int | None]:
        p = parse(raw)
        ids = self.db.by_postal.get(p.postal or "", [])
        return (ACCEPT, ids[0]) if ids else (FIX, None)
