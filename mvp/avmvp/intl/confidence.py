"""多市场结论的置信度：同一类结论在开发集真实地址上"位置给对"的实际比例（与新加坡 bayes.ConfidenceModel 同一做法）。

结论类别（签名）由引擎的证据组成，从细到粗四级：
  市场 | 结论 | 粒度 | 证据        例：ID|ACCEPT|ROUTE|area+postcode|exact|u1|-
  类别 | 结论 | 粒度 | 证据        例：C|ACCEPT|ROUTE|area+postcode|exact|u1|-
  类别 | 结论 | 粒度
  结论 | 粒度
细的一级样本少时向粗的一级收缩（Beta 先验，强度 strength），所以置信度天然是校准过的，也能解释：
"开发集上同类结论 N 条中位置给对了 M 条"。

拟合：python scripts/fit_intl_confidence.py（开发集拟合、测试集检验）；模型存为 models/confidence_intl.json。
"""

from __future__ import annotations

import json
from pathlib import Path

# 影响把握的原因码（其余原因码不进签名，避免类别过细）
NOTE_FLAGS = ("STREET_SPELL_CORRECTED", "STREET_PARTIAL_MATCH", "STREET_TRANSLITERATED", "POSTCODE_REPLACED",
              "POSTCODE_STREET_MISMATCH", "AREA_STREET_MISMATCH", "BUILDING_ONLY", "BUILDING_SPELL_CORRECTED", "BUILDING_NAME_AMBIGUOUS",
              "LANDMARK_RELATIVE", "LOCATED_BY_PLUS_CODE", "LOCATED_BY_COORDINATES", "AMBIGUOUS_MULTIPLE_CANDIDATES",
              "ROUTE_NOT_CORROBORATED", "MISSING_PREMISE", "PREMISE_NOT_FOUND", "UNIT_MISSING_MULTI_UNIT_BUILDING",
              "LLM_REWRITTEN", "LLM_UNVERIFIED")


def evidence(res) -> str:
    b = res.best
    if b is None:
        return "-"
    span = b.street_span
    how = span.how if span is not None else ("code" if b.code else "bldg" if b.building else "-")
    unique = "-" if span is None else "u1" if len(span.ids) == 1 else "uN"
    notes = "+".join(n for n in NOTE_FLAGS if n in res.reasons) or "-"
    return f"{'+'.join(sorted(b.support)) or 'none'}|{how}|{unique}|{notes}"


def signatures(res, market: str, cls: str) -> list[str]:
    head = f"{res.action}|{res.granularity}"
    ev = evidence(res)
    return [f"{market}|{head}|{ev}", f"{cls}|{head}|{ev}", f"{cls}|{head}", head]


class IntlConfidence:
    def __init__(self, table: dict[str, tuple[int, int]] | None = None, strength: float = 10.0):
        self.table = table or {}  # 签名 -> (位置给对的条数, 总条数)
        self.strength = strength

    def fit(self, items) -> "IntlConfidence":
        """items：(签名列表, 是否给对)；签名列表由 signatures(res, 市场, 类别) 得到。"""
        counts: dict[str, list[int]] = {}
        for sigs, correct in items:
            for sig in sigs:
                c = counts.setdefault(sig, [0, 0])
                c[0] += int(correct)
                c[1] += 1
        self.table = {k: (v[0], v[1]) for k, v in counts.items()}
        return self

    def confidence(self, res, market: str, cls: str) -> float:
        return self.from_signatures(signatures(res, market, cls))

    def from_signatures(self, sigs: list[str]) -> float:
        c, n = self.table.get(sigs[-1], (0, 0))
        est = (c + 1) / (n + 2)  # 最粗一级：Beta(1, 1)
        for sig in reversed(sigs[:-1]):
            c, n = self.table.get(sig, (0, 0))
            est = (c + self.strength * est) / (n + self.strength)
        return est

    def explain(self, res, market: str, cls: str) -> str:
        for sig in signatures(res, market, cls):
            c, n = self.table.get(sig, (0, 0))
            if n >= 5:
                return f"开发集上同类结论 {n} 条中位置给对了 {c} 条"
        return "开发集上同类结论很少，按更粗的类别估计"

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps({"strength": self.strength, "table": self.table}, ensure_ascii=False,
                                         indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "IntlConfidence":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls({k: tuple(v) for k, v in d["table"].items()}, d["strength"])
