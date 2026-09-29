"""贝叶斯打分（Fellegi–Sunter 概率匹配）：算出"这个候选就是用户所指地址"的概率。

做法：
1. 候选：沿用规则引擎召回的全部候选（邮编命中、楼栋+道路命中、楼宇名命中、规则给出的候选）
2. 逐字段比对：对每个候选，得到邮编 / 楼栋号 / 道路 / 楼宇名各自的"一致等级"（完全一致、差一位、没填、矛盾…）
3. 证据权重：每个字段每个等级有 m = P(该等级 | 候选正确)、u = P(该等级 | 候选错误)，权重 = log2(m / u)，
   m、u 从带标注的开发集统计（加一平滑）；各字段权重相加（朴素贝叶斯：假设字段之间条件独立）
4. 后验：所有候选加上"都不是"一起归一化，得到每个候选正确的概率
5. 校准：朴素贝叶斯常常过于自信，用留出数据拟合一个温度参数把概率拉回真实水平

相比规则引擎的手工优先级：权重来自数据、可以逐项展开解释，并且输出可直接用来设门槛的置信度。
"""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

from rapidfuzz import fuzz

from .normalize import match_key
from .parser import BLOCK_RE
from .validator import ACCEPT, CONFIRM, FIX, Analysis, Result, Validator

LEVELS: dict[str, list[str]] = {
    "postal": ["exact", "near", "absent", "mismatch"],      # near = 只差一位（常见手误）
    "block": ["exact", "letter", "absent", "mismatch"],     # letter = 数字相同、字母后缀不同（28 vs 28E）
    "street": ["exact", "corrected", "absent", "other"],    # other = 输入里有另一条真实道路
    "building": ["match", "absent", "nomatch"],
}

# 各严格度档位的门槛：(直接通过所需概率, 最低可建议概率)
THRESHOLDS = {"STRICT": (0.99, 0.8), "BALANCED": (0.95, 0.5), "LENIENT": (0.9, 0.3)}


def _digits(s: str) -> str:
    return "".join(c for c in s if c.isdigit())


def candidates(v: Validator, a: Analysis, limit: int = 30) -> list[int]:
    db, p = v.db, a.parsed
    out: list[int] = []

    def add(ids):
        for i in ids:
            if i not in out and len(out) < limit:
                out.append(i)

    add(a.postal_hits)
    for h in a.hypotheses:
        add(h.br)
    if a.result.entity is not None:
        add([a.result.entity.eid])
    add(a.result.candidates)
    if a.cfg.building_route:
        for h in a.hypotheses:
            if h.road is None and h.tokens:
                ids = (db.exact_building(h.tokens, p.country_suffix, p.country_prefix)
                       or db.find_building_entities(h.tokens, fuzzy=False, suffix=p.country_suffix))
                if len(ids) <= 5:
                    add(ids)
    return out


def compare(v: Validator, a: Analysis, eid: int) -> dict[str, str]:
    """输入与某个候选逐字段比对，返回各字段的一致等级。"""
    e, p = v.db.entities[eid], a.parsed
    if not p.postal:
        postal = "absent"
    elif p.postal == e.postal:
        postal = "exact"
    elif len(p.postal) == len(e.postal) and sum(x != y for x, y in zip(p.postal, e.postal)) == 1:
        postal = "near"
    else:
        postal = "mismatch"

    blocks = {h.blk for h in a.hypotheses if h.blk and not h.steal}
    if not blocks:
        block = "absent"
    elif e.blk in blocks:
        block = "exact"
    elif any(_digits(b) == _digits(e.blk) for b in blocks):
        block = "letter"
    else:
        block = "mismatch"

    roads = [h.road for h in a.hypotheses if h.road]
    mine = [r for r in roads if r.key == e.road_key]
    if mine:
        street = "exact" if any(r.exact for r in mine) else "corrected"
    elif any(r.exact for r in roads):
        street = "other"
    else:
        street = "absent"

    used = set(e.road_key.split()) | {e.blk}
    rest = [t for t in p.tokens if t not in used and not BLOCK_RE.match(t)]
    if not rest:
        building = "absent"
    elif e.buildings and max(fuzz.token_set_ratio(match_key(b), " ".join(rest)) for b in e.buildings) >= 90:
        building = "match"
    else:
        building = "nomatch"
    return {"postal": postal, "block": block, "street": street, "building": building}


def pattern(feats: dict[str, str]) -> str:
    return f"{feats['postal']}|{feats['block']}|{feats['street']}"


@dataclass
class BayesModel:
    weights: dict[str, dict[str, float]]  # 单字段证据权重 log2(m / u)
    prior_none: float  # 先验：真正的地址不在候选里（或根本没有地址）的比例
    temperature: float = 1.0
    m: dict | None = None
    u: dict | None = None
    # 联合证据：把"邮编 × 楼栋号 × 道路"的组合当作一个整体统计权重，捕捉字段之间的相互印证；
    # 样本太少的组合退回单字段权重之和。mode = "independent"（朴素）或 "joint"（联合）
    mode: str = "independent"
    joint: dict[str, float] | None = None

    def evidence(self, feats: dict[str, str]) -> float:
        if self.mode == "joint" and self.joint and pattern(feats) in self.joint:
            return self.joint[pattern(feats)] + self.weights["building"][feats["building"]]
        return sum(self.weights[k][feats[k]] for k in LEVELS)

    def posterior(self, v: Validator, a: Analysis) -> list[tuple[int | None, float, dict]]:
        """返回 [(实体 id 或 None=都不是, 概率, 比对等级)]，按概率从高到低。"""
        cands = candidates(v, a)
        feats = [compare(v, a, e) for e in cands]
        return self._normalize(cands, feats, self.temperature)

    def _normalize(self, cands, feats, temperature):
        if not cands:
            return [(None, 1.0, {})]
        each = (1 - self.prior_none) / len(cands)
        logits = [math.log2(self.prior_none)] + [math.log2(each) + self.evidence(f) for f in feats]
        logits = [x / temperature for x in logits]
        top = max(logits)
        w = [2 ** (x - top) for x in logits]
        z = sum(w)
        out = [(None, w[0] / z, {})] + [(e, w[i + 1] / z, feats[i]) for i, e in enumerate(cands)]
        return sorted(out, key=lambda x: -x[1])

    # ---------- 训练 ----------
    @classmethod
    def fit(cls, v: Validator, fit_rows: list[dict], calib_rows: list[dict], mode: str = "independent",
            alpha: float = 1.0, min_count: int = 5) -> "BayesModel":
        """fit_rows 统计 m / u 与先验；calib_rows 拟合温度。每行需要 input 与 expected_eid（None 表示没有正确地址）。"""
        m = {k: Counter() for k in LEVELS}
        u = {k: Counter() for k in LEVELS}
        jm, ju = Counter(), Counter()
        n_none = 0
        for r in fit_rows:
            a = v.analyze(r["input"])
            cands = candidates(v, a)
            if r["expected_eid"] is None or r["expected_eid"] not in cands:
                n_none += 1
            for e in cands:
                f = compare(v, a, e)
                is_true = e == r["expected_eid"]
                for k, lvl in f.items():
                    (m if is_true else u)[k][lvl] += 1
                (jm if is_true else ju)[pattern(f)] += 1

        def llr(mc, uc, mt, ut, n_levels):
            # 加 alpha 平滑；u 侧的伪计数按总量比例缩放，使"两边都没见过"的等级权重为 0（不偏向任何一方）
            scale = ut / max(mt, 1)
            return (math.log2((mc + alpha) / (mt + alpha * n_levels))
                    - math.log2((uc + alpha * scale) / (ut + alpha * scale * n_levels)))

        weights = {}
        for k, lvls in LEVELS.items():
            mt, ut = sum(m[k].values()), sum(u[k].values())
            weights[k] = {lv: llr(m[k][lv], u[k][lv], mt, ut, len(lvls)) for lv in lvls}
        n_pat = len(LEVELS["postal"]) * len(LEVELS["block"]) * len(LEVELS["street"])
        jmt, jut = sum(jm.values()), sum(ju.values())
        joint = {pt: llr(jm[pt], ju[pt], jmt, jut, n_pat) for pt in set(jm) | set(ju) if jm[pt] + ju[pt] >= min_count}
        model = cls(weights, (n_none + 1) / (len(fit_rows) + 2), 1.0,
                    {k: dict(c) for k, c in m.items()}, {k: dict(c) for k, c in u.items()}, mode, joint)

        prepared = []
        for r in calib_rows:
            a = v.analyze(r["input"])
            cands = candidates(v, a)
            prepared.append((cands, [compare(v, a, e) for e in cands], r["expected_eid"]))
        best_t, best_nll = 1.0, float("inf")
        for t in [0.5 + 0.25 * i for i in range(23)]:
            nll = 0.0
            for cands, feats, true in prepared:
                probs = {e: pr for e, pr, _ in model._normalize(cands, feats, t)}
                nll -= math.log(max(probs.get(true, 0.0), 1e-9))
            if nll < best_nll:
                best_t, best_nll = t, nll
        model.temperature = best_t
        return model

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps({"mode": self.mode, "weights": self.weights, "joint": self.joint,
                                          "prior_none": self.prior_none, "temperature": self.temperature,
                                          "m": self.m, "u": self.u}, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "BayesModel":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(d["weights"], d["prior_none"], d["temperature"], d.get("m"), d.get("u"),
                   d.get("mode", "independent"), d.get("joint"))


class ConfidenceModel:
    """规则结论的置信度：同一类结论在带标注数据里的实际正确率（Beta 先验平滑，稀有类别逐级退回更粗的类别）。

    结论类别（签名）由规则引擎的组件判定组成，例如"楼栋号确认 | 道路确认 | 邮编推断 | 无多余文字"。
    这样得到的置信度天然是校准过的，也能直接解释："历史上同类结论 N 条中对了 M 条"。
    """

    def __init__(self, table: dict[str, tuple[int, int]] | None = None, strength: float = 10.0):
        self.table = table or {}  # 签名 -> (正确数, 总数)
        self.strength = strength

    @staticmethod
    def signatures(res: Result) -> list[str]:
        """从细到粗的三级签名。"""
        if res.entity is None:
            reasons = sorted(set(res.reasons) - {"NON_ADDRESS_INFO_EXTRACTED", "LOW_CONFIDENCE"})
            return ["FIX:" + "+".join(reasons), "FIX:" + (reasons[0] if reasons else ""), "FIX"]
        st = res.status
        core = f"{st.get('premise')}|{st.get('route')}|{st.get('postal')}"
        flags = (f"bld={'y' if res.building_confirmed else 'n'}|unres={'y' if res.unresolved else 'n'}"
                 f"|poi={'y' if 'BUILDING_NAME_ONLY' in res.reasons else 'n'}")
        return [f"ENTITY:{core}|{flags}", f"ENTITY:{core}", "ENTITY"]

    def fit(self, results_and_truth) -> "ConfidenceModel":
        counts: dict[str, list[int]] = {}
        for res, correct in results_and_truth:
            for sig in self.signatures(res):
                c = counts.setdefault(sig, [0, 0])
                c[0] += int(correct)
                c[1] += 1
        self.table = {k: (v[0], v[1]) for k, v in counts.items()}
        return self

    def confidence(self, res: Result) -> float:
        est = 0.5  # 最粗一级之上的先验：Beta(1, 1)
        for sig in reversed(self.signatures(res)):
            c, n = self.table.get(sig, (0, 0))
            est = (c + self.strength * est) / (n + self.strength) if sig not in ("ENTITY", "FIX") else (c + 1) / (n + 2)
        return est

    def explain(self, res: Result) -> str:
        sig = self.signatures(res)[0]
        c, n = self.table.get(sig, (0, 0))
        return f"历史上同类结论 {n} 条中对了 {c} 条" if n else "历史上没有同类结论，按更粗的类别估计"

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps({"strength": self.strength, "table": self.table}, ensure_ascii=False,
                                         indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "ConfidenceModel":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls({k: tuple(v) for k, v in d["table"].items()}, d["strength"])


class ConfidenceValidator:
    """规则负责"选哪个"，贝叶斯置信度负责"有多大把握"：把握不足时把 ACCEPT 降为 CONFIRM，不改变选中的地址。"""

    def __init__(self, validator: Validator, model: ConfidenceModel, thresholds: dict | None = None):
        self.v, self.model = validator, model
        self.db = validator.db
        self.thresholds = thresholds or THRESHOLDS

    def to_response(self, res: Result) -> dict:
        return self.v.to_response(res)

    def validate(self, raw: str, strictness: str | None = None) -> Result:
        profile = strictness or self.v.config.strictness
        res = self.v.validate(raw, strictness)
        res.confidence = self.model.confidence(res)
        if res.action == ACCEPT and res.confidence < self.thresholds[profile][0]:
            res.action = CONFIRM
            res.reasons.append("LOW_CONFIDENCE")
        return res


class BayesValidator:
    """规则引擎负责召回候选与组件描述，贝叶斯打分负责"选哪个"和"有多大把握"。"""

    def __init__(self, validator: Validator, model: BayesModel, thresholds: dict | None = None):
        self.v, self.model = validator, model
        self.db = validator.db
        self.thresholds = thresholds or THRESHOLDS

    def to_response(self, res: Result) -> dict:
        return self.v.to_response(res)

    def validate(self, raw: str, strictness: str | None = None) -> Result:
        profile = strictness or self.v.config.strictness
        accept_t, confirm_t = self.thresholds[profile]
        a = self.v.analyze(raw, strictness)
        post = self.model.posterior(self.v, a)
        best, pb, _ = post[0]
        rule = a.result
        if best is None or pb < confirm_t:
            if rule.action == FIX:
                res = rule
            else:
                res = replace(rule, action=FIX, entity=None, status={}, reasons=[*rule.reasons, "LOW_CONFIDENCE"],
                              candidates=[e for e, _, _ in post if e is not None][:5])
            res.confidence = next(pr for e, pr, _ in post if e is None)  # "没有可用地址"的概率
            return res
        if rule.entity is not None and rule.entity.eid == best:
            res = rule
        else:
            res = self.v.describe(a, best)
            res.reasons.append("BAYES_RESELECTED")
        res.confidence = pb
        if res.action == ACCEPT and pb < accept_t:
            res.action = CONFIRM
            res.reasons.append("LOW_CONFIDENCE")
        return res
