"""多市场校验引擎：解析 -> 召回候选 -> 证据打分 -> 结论 / 粒度 / 坐标 -> Google AV 风格响应。

证据（与新加坡引擎同一思路：多个字段相互印证才可信）：
  道路     名称完全一致 > 去掉类型词后一致 > 容错匹配
  片区     道路落在所写片区的边界内（或附近）
  邮编     道路 / 地址点在该邮编的范围内
  楼宇     所写楼宇 / POI 在道路附近
  地址点   A 类市场：官方地址表里有"这条路 + 这个门牌"

结论（BALANCED 档）：
  A 类  地址点确认 -> ACCEPT（道路纠错 / 邮编被替换 -> CONFIRM；楼内有多个单元却没写 -> 补单元号）；
        道路确认但门牌不存在 / 没写 -> FIX
  B / C 类  没有地址点，最高验到"道路 + 片区一致、有门牌或楼名"-> ACCEPT（门牌标为"合理但未证实"）；
        楼宇 / POI 匹配 -> ACCEPT 或 CONFIRM；只到片区 -> FIX
"""

from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass, field

import numpy as np

from .markets import MARKETS
from .parse import Parsed, RuleParser, Span
from .pluscode import encode, recover
from .reference import MarketReference, haversine, number_key
from .text import fmt_postcode, fold, postcode_prefix, script_of

ACCEPT, CONFIRM, FIX, ADD_SUB = "ACCEPT", "CONFIRM", "FIX", "CONFIRM_ADD_SUBPREMISES"
# 参照物描述：说明写的楼不是地址本身（behind / opposite / near …，阿拉伯文 خلف / مقابل / بجانب / قرب）
LANDMARK = re.compile(r"\b(?:BEHIND|OPPOSITE|OPP|NEAR|NEXT TO|BESIDE|ACROSS|IN FRONT OF|ADJACENT TO|"
                      r"DEPAN|BELAKANG|SEBELAH|DEKAT|BERHADAPAN|TRUOC|SAU|GAN|KE BEN)\b|خلف|مقابل|بجانب|قرب|امام", re.I)
BASE = {"exact": 3.0, "core": 2.6, "thai": 2.4, "partial": 2.2, "crf": 2.2, "translit": 2.2}


@dataclass
class Hypothesis:
    score: float
    street: int | None = None
    street_span: Span | None = None
    area: int | None = None
    building: dict | None = None
    point: dict | None = None  # A 类地址点
    code: tuple[float, float, float] | None = None  # Plus Code 解码出的位置（纬度, 经度, 格子边长米）
    notes: list[str] = field(default_factory=list)
    support: set[str] = field(default_factory=set)  # 相互印证的字段：area / postcode / building / point


@dataclass
class Result:
    market: str
    action: str
    granularity: str  # PREMISE / PREMISE_PROXIMITY / ROUTE / LOCALITY / OTHER
    lat: float | None
    lng: float | None
    parsed: Parsed
    best: Hypothesis | None
    reasons: list[str]
    components: dict[str, dict]
    candidates: list[dict]
    parser: str
    confidence: float | None = None  # 校准过的置信度（有置信度模型时在 validate 里算好）
    confidence_note: str = ""

    @property
    def location(self):
        return (self.lat, self.lng) if self.lat is not None else None


def _street_array(ref: MarketReference, sid: int) -> np.ndarray:
    """道路沿线点（弧度），按道路缓存。"""
    cache = ref.__dict__.setdefault("_np", {})
    a = cache.get(sid)
    if a is None:
        s = ref.streets[sid]
        a = cache[sid] = np.radians(np.asarray(s.points or [(s.lat, s.lng)], dtype=float))
    return a


def _haversine_many(a: np.ndarray, lat: float, lng: float) -> np.ndarray:
    la, ln = math.radians(lat), math.radians(lng)
    h = np.sin((a[:, 0] - la) / 2) ** 2 + math.cos(la) * np.cos(a[:, 0]) * np.sin((a[:, 1] - ln) / 2) ** 2
    return 12742000 * np.arcsin(np.sqrt(np.minimum(h, 1.0)))


def dist_to_street(ref: MarketReference, sid: int, lat: float, lng: float) -> float:
    """点到道路的距离（米）：到最近沿线点的距离，减去点间距的一半作余量。"""
    return max(float(_haversine_many(_street_array(ref, sid), lat, lng).min()) - 40, 0.0)


def nearest_point(ref: MarketReference, sid: int, lat: float, lng: float) -> tuple[float, float]:
    s = ref.streets[sid]
    if not s.points:
        return s.lat, s.lng
    return s.points[int(_haversine_many(_street_array(ref, sid), lat, lng).argmin())]


class Engine:
    """parser：rules / crf / hybrid（规则 + 机器学习都出候选）/ llm（只用本地小模型）。
    llm：可选的本地小模型客户端（见 llm.py）。给了它，hybrid 在没有直接通过时再请模型拆一次字段（级联）。"""

    def __init__(self, market: str, parser: str = "rules", ref: MarketReference | None = None, llm=None,
                 confidence=None, policy: dict | None = None):
        self.market = market
        self.m = MARKETS[market]
        # 直接通过的放宽规则（按市场在开发集上校准，见 scripts/fit_accept_policy.py）；policy={} 表示不用
        self.policy = set((load_policy() if policy is None else policy).get(market, []))
        self.conf_model = confidence  # 可选：IntlConfidence（校准过的置信度，见 confidence.py）
        self.ref = ref or MarketReference.load(market)
        self.rules = RuleParser(self.ref)
        self.crf = None
        self.parser = parser
        if parser in ("crf", "hybrid"):
            from .crf import CRFParser
            self.crf = CRFParser(self.ref)
        self.llm = None
        if llm is not None or parser == "llm":
            from .llm import LLMParser
            self.llm = LLMParser(self.ref, llm)

    # ------------------------------------------------------------------ 入口
    def validate(self, text: str, strictness: str = "BALANCED", min_confidence: float | None = None) -> Result:
        """min_confidence：可选门槛。结论是 ACCEPT（或只提示补单元号）但置信度低于门槛时，改为 CONFIRM（LOW_CONFIDENCE）。"""
        res = self._validate(text, strictness)
        if self.conf_model is not None and res.lat is not None:
            res.confidence = self.conf_model.confidence(res, self.market, self.m.cls)
            res.confidence_note = self.conf_model.explain(res, self.market, self.m.cls)
            if min_confidence is not None and res.action in (ACCEPT, ADD_SUB) and res.confidence < min_confidence:
                res.action = CONFIRM  # 置信度保持按原结论计算，让调用方看得到为什么被降级
                res.reasons.append("LOW_CONFIDENCE")
        return res

    def _validate(self, text: str, strictness: str) -> Result:
        if self.parser == "llm":
            p = self.llm.parse(text)
            parses = [p] if p is not None else [self.rules.parse(text)]
        elif self.parser == "rules":
            parses = [self.rules.parse(text)]
        elif self.parser == "crf":
            parses = [self.crf.parse(text)]
        else:  # 混合：两种解析都生成候选，由参考数据决定
            parses = [self.rules.parse(text), self.crf.parse(text)]
        best_res = None
        for p in parses:
            res = self._llm_cap(self._decide(p, strictness))
            if best_res is None or _rank(res) > _rank(best_res):
                best_res = res
        best_res.parser = self.parser
        if self.llm is not None and self.parser != "llm" and best_res.action != ACCEPT:
            # 级联：规则 + 机器学习没能直接通过时，请本地小模型再拆一次字段，结果同样由参考数据裁决
            p = self.llm.parse(text)
            if p is not None:
                # 两种用法都试：只用模型拆出的字段；把模型补出的字段并入规则解析（规则认出道路、模型认出片区 / 楼名）
                for cand in (p, _merge(best_res.parsed, p)):
                    res = self._llm_cap(self._decide(cand, strictness))
                    if _rank(res) > _rank(best_res):
                        res.parser = self.parser + "+llm"
                        best_res = res
        return best_res

    def _llm_cap(self, res: Result) -> Result:
        """模型解析出的结果：改写过原文的最多给 CONFIRM；没有官方地址表的市场（B / C 类）一律最多 CONFIRM
        （开发集上，模型结果在这些市场直接通过时偏差 >1 公里的错误明显增加）。"""
        if res.parsed.parser == "llm" and res.action in (ACCEPT, ADD_SUB):
            if not getattr(res.parsed, "verbatim", True):
                res.action = CONFIRM
                res.reasons.append("LLM_REWRITTEN")
            elif not self.ref.has_addresses:
                res.action = CONFIRM
                res.reasons.append("LLM_UNVERIFIED")
        return res

    # ------------------------------------------------------------------ 候选与打分
    def _hypotheses(self, p: Parsed) -> list[Hypothesis]:
        ref = self.ref
        pc = ref.postcodes.get(p.postcode) if p.postcode and self.m.postcode else None
        if pc is None and p.postcode and self.m.postcode:  # 一户一码的邮编（爱尔兰、英国）：按上一级片区印证
            pc = getattr(ref, "postcode_prefix", {}).get(postcode_prefix(p.postcode, self.market))
        pc_unknown = bool(p.postcode and self.m.postcode and getattr(ref, "pc_complete", ref.has_addresses)
                          and pc is None)
        area_ids = [a for s in p.areas for a in s.ids][:30]
        hyps: list[Hypothesis] = []
        buildings = []
        for b in p.buildings[:3]:
            for pid in b.ids[:10]:
                buildings.append((b, ref.poi(pid)))
        for span in p.streets[:6]:
            ids = span.ids
            if len(ids) > 40:  # 名称太常见（如 Jalan 3）：先用片区 / 邮编 / 楼宇缩小
                ids = self._narrow(ids, area_ids, pc, buildings) or ids[:40]
            for sid in ids:
                s = ref.streets[sid]
                h = Hypothesis(BASE.get(span.how, 1.0 + max(span.score - 86, 0) / 14 * 1.2), sid, span)
                if span.how == "fuzzy":
                    h.notes.append("STREET_SPELL_CORRECTED")
                elif span.how == "partial":
                    h.notes.append("STREET_PARTIAL_MATCH")
                elif span.how == "translit":
                    h.notes.append("STREET_TRANSLITERATED")
                self._area_evidence(h, s, area_ids)
                if pc_unknown:  # A 类地址表是全量的：查无此邮编说明邮编错了或不在覆盖范围
                    h.score -= 1.5
                    h.notes.append("POSTCODE_NOT_FOUND")
                if pc:
                    d = dist_to_street(ref, sid, pc[0], pc[1])
                    if d <= 1500:
                        h.score += 1.5
                        h.support.add("postcode")
                    elif d > 5000:
                        h.score -= 1.5
                        h.notes.append("POSTCODE_STREET_MISMATCH")
                for b, poi in buildings:
                    if dist_to_street(ref, sid, poi["lat"], poi["lng"]) <= 400:
                        h.score += 1.5 if b.score >= 97 else 1.0
                        h.building = poi
                        h.support.add("building")
                        self._building_notes(h, b, p)
                        break
                if ref.has_addresses:
                    self._premise(h, p)
                hyps.append(h)
        for b, poi in buildings:  # 只凭楼宇 / POI
            h = Hypothesis(1.5 + (0.8 if b.score >= 97 else 0), building=poi)
            h.notes.append("BUILDING_ONLY")
            self._building_notes(h, b, p)
            if area_ids and poi["area"] in area_ids:
                h.score += 1.5
            if pc and haversine(poi["lat"], poi["lng"], pc[0], pc[1]) <= 2000:
                h.score += 1.0
            hyps.append(h)
        code = self._plus_code(p)
        if code:  # Plus Code：直接给出约 14 米见方的位置；与所写道路核对
            h = Hypothesis(6.0, code=code)
            h.notes.append("LOCATED_BY_COORDINATES" if "latlng" in p.codes else "LOCATED_BY_PLUS_CODE")
            areas = [ref.areas[a] for sp in p.areas for a in sp.ids[:5]]
            if areas and all(haversine(a.lat, a.lng, code[0], code[1]) > max(a.radius_m * 1.5, 2000) for a in areas):
                h.notes.append("PLUS_CODE_AREA_MISMATCH")
            streets = sorted((x for x in hyps if x.street is not None), key=lambda x: -x.score)
            near = [x for x in streets if dist_to_street(ref, x.street, code[0], code[1]) <= 300]
            if near:
                h.street, h.street_span, h.area = near[0].street, near[0].street_span, near[0].area
                h.support.add("street")
            elif streets:
                h.notes.append("PLUS_CODE_STREET_MISMATCH")
            hyps.append(h)
        if not hyps and ref.has_addresses and p.postcode and p.number:  # A 类：只有邮编 + 门牌
            for pt in ref.db.execute("SELECT id, number, street, unit, postcode, locality, lat, lng FROM addr "
                                     "WHERE postcode=? AND number_key=? LIMIT 20",
                                     (p.postcode, p.number.replace(" ", "").upper())).fetchall():
                h = Hypothesis(2.0, street=pt[2], point=dict(zip(("id", "number", "street", "unit", "postcode",
                                                                   "locality", "lat", "lng"), pt)))
                h.notes.append("STREET_INFERRED")
                hyps.append(h)
        return sorted(hyps, key=lambda h: -h.score)

    def _building_notes(self, h: Hypothesis, b: Span, p: Parsed) -> None:
        """楼名靠纠错才对上（FMC -> NMC Medical Center）、只是参照物（Behind Mall of Emirates）、
        或同名楼宇分布在相距 1 公里以上的多处（迪拜的 Galleria Mall、The Boulevard）：靠楼宇定位时不能直接通过。"""
        if b.score < 97:
            h.notes.append("BUILDING_SPELL_CORRECTED")
        if LANDMARK.search(fold(p.raw)):
            h.notes.append("LANDMARK_RELATIVE")
        if len(b.ids) > 1:
            pts = [self.ref.poi(i) for i in b.ids[:10]]
            if any(haversine(a["lat"], a["lng"], c["lat"], c["lng"]) > 1000 for a in pts for c in pts):
                h.notes.append("BUILDING_NAME_AMBIGUOUS")

    def _plus_code(self, p: Parsed) -> tuple[float, float, float] | None:
        if "latlng" in p.codes:  # 直接贴的坐标：与 Plus Code 同样处理
            lat, lng = map(float, p.codes["latlng"].split(","))
            if any(b[1] - 0.3 <= lat <= b[3] + 0.3 and b[0] - 0.3 <= lng <= b[2] + 0.3 for _, b in self.m.regions):
                return lat, lng, 10.0
        raw = p.codes.get("plus_code")
        if not raw:
            return None
        if p.areas and p.areas[0].ids:  # 短码按所写片区补齐，否则按试点城市中心
            a = self.ref.areas[p.areas[0].ids[0]]
            ref_lat, ref_lng = a.lat, a.lng
        else:
            b = self.m.regions[0][1]
            ref_lat, ref_lng = (b[1] + b[3]) / 2, (b[0] + b[2]) / 2
        res = recover(raw, ref_lat, ref_lng)
        if res is None or not any(b[1] - 0.3 <= res[0] <= b[3] + 0.3 and b[0] - 0.3 <= res[1] <= b[2] + 0.3
                                  for _, b in self.m.regions):
            return None
        return res

    def _area_at(self, lat: float, lng: float):
        """点所在（或最近）的最小片区。"""
        near = [a for a in self.ref.areas if haversine(a.lat, a.lng, lat, lng) <= a.radius_m]
        return min(near, key=lambda a: a.radius_m) if near else None

    def _narrow(self, ids, area_ids, pc, buildings) -> list[int]:
        ref = self.ref
        keep = [i for i in ids if set(ref.streets[i].areas) & set(area_ids)]
        if not keep and pc:
            keep = [i for i in ids if dist_to_street(ref, i, pc[0], pc[1]) <= 2000]
        if not keep and buildings:
            keep = [i for i in ids if any(dist_to_street(ref, i, poi["lat"], poi["lng"]) <= 400
                                          for _, poi in buildings)]
        return keep[:40]

    def _area_evidence(self, h: Hypothesis, s, area_ids: list[int]) -> None:
        if not area_ids:
            return
        inside = [a for a in area_ids if a in s.areas]
        if inside:
            h.score += 2.0
            h.area = inside[0]
            h.support.add("area")
            return
        near = [a for a in area_ids
                if dist_to_street(self.ref, s.id, self.ref.areas[a].lat, self.ref.areas[a].lng)
                <= self.ref.areas[a].radius_m]
        if near:
            h.score += 1.2
            h.area = near[0]
            h.support.add("area")
        elif any(self.ref.areas[a].has_poly for a in area_ids):  # 没有边界的片区范围不确定，不扣分
            h.score -= 1.0
            h.notes.append("AREA_STREET_MISMATCH")

    def _premise(self, h: Hypothesis, p: Parsed) -> None:
        if not p.number:
            return
        pts = []
        for num in self._number_variants(p.number):
            pts = self.ref.addresses([h.street], num)
            if pts:
                # 门牌原样一致的地址点优先于"只是其中一部分号码"一致的（Kopli 16 优先于 Kopli 103/16）
                pts.sort(key=lambda x: number_key(x["number"]) != number_key(num))
                break
        if not pts:
            near = self._nearby_number(h.street, p.number)
            if near is not None:  # 门牌不在官方表里，但同一条路上紧挨着的门牌在：位置可信，请用户确认门牌
                h.point = near
                h.score += 2.5
                h.notes.append("PREMISE_INTERPOLATED")
                h.support.add("point")
                return
        if pts and p.unit:  # 同一门牌下优先取单元号一致的地址点
            want = re.sub(r"^(?:UNIT|APARTMENT|SUITE|FLAT|SHOP)\s*", "", p.unit.upper())
            pts = [x for x in pts if (x["unit"] or "").upper().replace("UNIT ", "") == want] or pts
        if not pts:
            h.score -= 1.0
            h.notes.append("PREMISE_NOT_FOUND")
            return
        if p.postcode and any(x["postcode"] for x in pts):  # 有的国家地址表不带邮编，就不比
            same = [x for x in pts if x["postcode"] == p.postcode]
            if same:
                pts = same
                h.score += 1.0
            else:
                h.notes.append("POSTCODE_REPLACED")
        h.point = pts[0]
        h.score += 4.0
        h.support.add("point")

    def _nearby_number(self, street: int, number: str) -> dict | None:
        """门牌不在官方表里时，找同一条路上紧挨着的门牌（同侧优先）：
        - 一般门牌：±2、±4、±6，再试 ±1、±3、±5（12A 先试 12）
        - 哥伦比亚 # 31-10：同一个街区（31-*）里距离数最接近的门牌（相差 40 米以内）
        日本的街区号不按位置顺序编排，不推算。"""
        n = number.replace(" ", "").upper()
        if self.market == "JP":
            return None
        m = re.fullmatch(r"(\d+[A-Z]?)-(\d+)", n)
        if self.market == "CO" and m:
            rows = self.ref.db.execute(
                "SELECT id, number, street, unit, postcode, locality, lat, lng FROM addr WHERE street=? AND "
                "number_key LIKE ? LIMIT 200", (street, m.group(1) + "-%")).fetchall()
            best = None
            for r in rows:
                tail = r[1].split("-")[-1]
                if tail.isdigit() and abs(int(tail) - int(m.group(2))) <= 40 and (
                        best is None or abs(int(tail) - int(m.group(2))) < abs(int(best[1].split("-")[-1]) - int(m.group(2)))):
                    best = r
            return dict(zip(("id", "number", "street", "unit", "postcode", "locality", "lat", "lng"), best)) \
                if best else None
        m = re.fullmatch(r"(\d+)([A-Z]?)", n)
        if not m:
            return None
        base = int(m.group(1))
        tries = ([str(base)] if m.group(2) else []) + [str(base + d) for d in (2, -2, 4, -4, 6, -6, 1, -1, 3, -3, 5, -5)
                                                       if base + d > 0]
        for t in tries:
            pts = self.ref.addresses([street], t)
            if pts:
                return pts[0]
        return None

    def _number_variants(self, number: str) -> list[str]:
        """门牌号的等价写法：51-55（区间，官方表可能只记首尾之一）、12 A / 12A。"""
        n = number.replace(" ", "").upper()
        out = [n]
        m = re.fullmatch(r"(\d+[A-Z]?)-(\d+[A-Z]?)", n)
        if m and self.market == "JP":  # 日本 7-9（番地-号）：地址表只到街区（番地），按街区查
            out.append(m.group(1))
        elif m and self.market not in ("NL", "CO"):  # 哥伦比亚 66-33 是一个整体
            out += [m.group(1), m.group(2)]
        m = re.fullmatch(r"(\d+[A-Z]?)/(\d+[A-Z]?)", n)
        if m:  # 斯洛伐克 / 捷克 2132/1：只写了其中一个号码时也能查到（参考库三种写法都有）
            out += [m.group(2), m.group(1)]
        return out

    # ------------------------------------------------------------------ 结论
    def _decide(self, p: Parsed, strictness: str) -> Result:
        ref = self.ref
        hyps = self._hypotheses(p)
        reasons: list[str] = []
        if p.noise:
            reasons.append("NON_ADDRESS_INFO_EXTRACTED")
        best = hyps[0] if hyps else None
        # 次优候选：不同道路、分数接近、相距较远 -> 有歧义
        ambiguous = False
        if best and len(hyps) > 1:
            for h in hyps[1:4]:
                if h.street != best.street and best.score - h.score < 0.6 and _far(ref, best, h):
                    ambiguous = True
                    break
        # 同名道路很多（迪拜各社区都有 6th Street、Jalan 3）又没有片区 / 邮编 / 楼宇 / 地址点能区分：不能直接通过
        if best and best.street is not None and best.street_span is not None and len(best.street_span.ids) > 1 \
                and not best.support:
            ambiguous = True
        comps: dict[str, dict] = {}
        lat = lng = None
        if best is None:
            gran, action = "OTHER", FIX
            loc = self._area_or_postcode(p)
            if loc:
                gran, lat, lng = "LOCALITY", loc[0], loc[1]
                reasons.append("ONLY_LOCALITY")
            else:
                reasons.append("NO_MATCH")
            return Result(self.market, action, gran, lat, lng, p, None, reasons, comps, [], p.parser)

        reasons += best.notes
        if best.point:
            gran = "PREMISE_PROXIMITY" if "PREMISE_INTERPOLATED" in best.notes else "PREMISE"
            lat, lng = best.point["lat"], best.point["lng"]
        elif best.code:
            gran, lat, lng = "PREMISE_PROXIMITY", best.code[0], best.code[1]
        elif best.building and best.street is None:
            gran, lat, lng = "PREMISE_PROXIMITY", best.building["lat"], best.building["lng"]
        elif best.building:
            gran, lat, lng = "PREMISE_PROXIMITY", best.building["lat"], best.building["lng"]
        else:
            gran = "ROUTE"
            lat, lng = self._route_point(best, p)
        if best.street is not None:
            s = ref.streets[best.street]
            comps["route"] = {"text": _display(s.names, p.raw), "level": "CONFIRMED" if best.street_span and
                              best.street_span.how not in ("fuzzy", "partial") else "UNCONFIRMED_BUT_PLAUSIBLE",
                              "spellCorrected": "STREET_SPELL_CORRECTED" in best.notes,
                              "inferred": best.street_span is None}
        if best.area is not None:
            comps["locality"] = {"text": _display(ref.areas[best.area].names, p.raw), "level": "CONFIRMED"}
        elif best.point and best.point.get("locality"):  # A 类：官方地址表里的地名
            comps["locality"] = {"text": best.point["locality"], "level": "CONFIRMED", "inferred": True}
        elif best.code:  # 只有 Plus Code / 坐标：补上所在片区
            a = self._area_at(best.code[0], best.code[1])
            if a is not None:
                comps["locality"] = {"text": _display(a.names, p.raw), "level": "CONFIRMED", "inferred": True}
        if best.code:
            comps["plus_code"] = {"text": encode(best.code[0], best.code[1]), "level": "CONFIRMED"}
        if best.building:
            comps["premise_name"] = {"text": best.building["name"], "level": "CONFIRMED"}
        if p.number:
            exact = best.point and "PREMISE_INTERPOLATED" not in best.notes
            comps["street_number"] = {"text": best.point["number"] if exact else p.number,
                                      "level": "CONFIRMED" if exact else "UNCONFIRMED_BUT_PLAUSIBLE"}
        if p.postcode:
            comps["postal_code"] = {"text": best.point["postcode"] if best.point else p.postcode,
                                    "level": "CONFIRMED" if (best.point and best.point["postcode"] == p.postcode)
                                    or "POSTCODE_STREET_MISMATCH" not in best.notes else "UNCONFIRMED_AND_SUSPICIOUS",
                                    "replaced": "POSTCODE_REPLACED" in best.notes}
        elif best.point and best.point.get("postcode"):
            comps["postal_code"] = {"text": best.point["postcode"], "level": "CONFIRMED", "inferred": True}
            reasons.append("POSTCODE_INFERRED")
        if p.unit:
            comps["subpremise"] = {"text": p.unit, "level": "UNCONFIRMED_BUT_PLAUSIBLE"}

        action = self._action(p, best, gran, ambiguous, reasons, strictness)
        cands = [self._describe(h) for h in hyps[:5]] if action != ACCEPT else []
        return Result(self.market, action, gran, lat, lng, p, best, reasons, comps, cands, p.parser)

    def _action(self, p: Parsed, best: Hypothesis, gran: str, ambiguous: bool, reasons: list[str],
                strictness: str) -> str:
        # 楼名纠错 / 参照物只在"靠楼宇定位"（PREMISE_PROXIMITY）时影响结论；门牌已由官方地址点确认时不影响
        weak_building = gran == "PREMISE_PROXIMITY" and bool(
            {"BUILDING_SPELL_CORRECTED", "LANDMARK_RELATIVE", "BUILDING_NAME_AMBIGUOUS"} & set(best.notes))
        corrected = weak_building or any(n in best.notes for n in (
            "STREET_SPELL_CORRECTED", "STREET_PARTIAL_MATCH", "POSTCODE_REPLACED", "POSTCODE_NOT_FOUND",
            "POSTCODE_STREET_MISMATCH", "AREA_STREET_MISMATCH", "STREET_INFERRED"))
        if ambiguous:
            reasons.append("AMBIGUOUS_MULTIPLE_CANDIDATES")
            return CONFIRM
        if self.ref.has_addresses:  # A 类
            if gran == "PREMISE":
                # 只有邮编被替换、而这个市场开发集上"门牌对上 + 邮编被替换"的结论几乎都对（萨格勒布通写 10000、
                # 立陶宛邮编细到路段）：不算纠正
                if corrected and strictness != "STRICT" and policy_key_premise(best) in self.policy:
                    corrected = False
                if not p.unit and best.point and self.ref.units_at(best.point["street"], best.point["number"]) > 1:
                    reasons.append("UNIT_MISSING_MULTI_UNIT_BUILDING")
                    return CONFIRM if corrected else ADD_SUB
                if corrected or (strictness == "STRICT" and "POSTCODE_INFERRED" in reasons):
                    return CONFIRM
                return ACCEPT
            if gran == "PREMISE_PROXIMITY":
                return CONFIRM
            reasons.append("MISSING_PREMISE" if not p.number else "PREMISE_NOT_FOUND"
                           if "PREMISE_NOT_FOUND" not in reasons else "PREMISE_NOT_FOUND")
            return FIX
        # B / C 类
        has_premise = bool(p.number or best.building or p.codes)
        if gran == "PREMISE_PROXIMITY" and best.code:
            conflict = {"PLUS_CODE_STREET_MISMATCH", "PLUS_CODE_AREA_MISMATCH"} & set(best.notes)
            return CONFIRM if conflict or strictness == "STRICT" else ACCEPT
        if gran == "PREMISE_PROXIMITY":
            if best.street is None:
                return CONFIRM if "BUILDING_ONLY" in best.notes and best.score < 3.0 else (
                    ACCEPT if strictness == "LENIENT" else CONFIRM)
            return CONFIRM if corrected else ACCEPT
        if gran == "ROUTE":
            if not has_premise:
                reasons.append("MISSING_PREMISE")
                return CONFIRM
            if corrected:
                return CONFIRM
            # 道路级直接通过的条件（按开发集校准，见 docs/13）：邮编与道路相互印证、道路名在试点城市里唯一，
            # 且名称完全一致或片区也印证。只有片区印证、或同名道路不止一条时，偏差超过 1 公里的比例在 10% 以上
            span = best.street_span
            unique = span is not None and len(span.ids) == 1
            strong = "postcode" in best.support and unique and (span.how == "exact" or "area" in best.support)
            if not strong and policy_key_route(best) in self.policy:
                strong = True  # 这个市场开发集上同样证据组合的道路级结论几乎都对（见 fit_accept_policy.py）
            if not strong or strictness == "STRICT":
                if strictness != "LENIENT" or not (best.support and unique):
                    reasons.append("ROUTE_NOT_CORROBORATED")
                    return CONFIRM
            return ACCEPT
        return FIX

    def _route_point(self, h: Hypothesis, p: Parsed) -> tuple[float, float]:
        """道路级定位：长路取离片区 / 邮编最近的路段，否则取道路中心。"""
        ref = self.ref
        anchor = None
        if h.area is not None:
            anchor = (ref.areas[h.area].lat, ref.areas[h.area].lng)
        elif p.postcode and p.postcode in ref.postcodes and self.m.postcode:
            anchor = ref.postcodes[p.postcode][:2]
        if anchor:
            return nearest_point(ref, h.street, anchor[0], anchor[1])
        s = ref.streets[h.street]
        return s.lat, s.lng

    def _area_or_postcode(self, p: Parsed):
        if p.areas and p.areas[0].ids:
            a = self.ref.areas[p.areas[0].ids[0]]
            return a.lat, a.lng
        if p.postcode and self.m.postcode and p.postcode in self.ref.postcodes:
            c = self.ref.postcodes[p.postcode]
            return c[0], c[1]
        return None

    def _describe(self, h: Hypothesis) -> dict:
        out = {"score": round(h.score, 2)}
        if h.street is not None:
            s = self.ref.streets[h.street]
            out.update(street=s.name, lat=s.lat, lng=s.lng)
        if h.point:
            out.update(number=h.point["number"], postcode=h.point["postcode"], lat=h.point["lat"], lng=h.point["lng"])
        if h.building:
            out.update(building=h.building["name"])
        if h.area is not None:
            out.update(area=self.ref.areas[h.area].name)
        if h.code:
            out.update(lat=h.code[0], lng=h.code[1])
        return out

    # ------------------------------------------------------------------ 响应
    def to_response(self, res: Result) -> dict:
        """Google AV 风格的响应（字段含义与新加坡引擎一致，见 docs/13）。"""
        names = {"route": "route", "locality": "sublocality", "premise_name": "premise_name",
                 "street_number": "street_number", "postal_code": "postal_code", "subpremise": "subpremise",
                 "plus_code": "plus_code"}
        comps = []
        for k, v in res.components.items():
            text = fmt_postcode(v["text"], self.market) if k == "postal_code" else v["text"]
            c = {"componentType": names[k], "componentName": {"text": text}, "confirmationLevel": v["level"]}
            c.update({f: True for f in ("inferred", "spellCorrected", "replaced") if v.get(f)})
            comps.append(c)
        missing = [t for t, k in (("route", "route"), ("street_number", "street_number"))
                   if k not in res.components and not (k == "street_number" and res.best and res.best.building)]
        levels = [c["confirmationLevel"] for c in comps]
        return {"responseId": str(uuid.uuid4()), "result": {
            "verdict": {"possibleNextAction": res.action, "validationGranularity": res.granularity,
                        **({"confidence": round(res.confidence, 4),
                            "confidenceNote": res.confidence_note}
                           if res.confidence is not None else {}),
                        "geocodeGranularity": res.granularity,
                        "addressComplete": res.action == ACCEPT,
                        "hasUnconfirmedComponents": any(x != "CONFIRMED" for x in levels) or res.best is None,
                        "hasInferredComponents": any(c.get("inferred") for c in res.components.values()),
                        "hasReplacedComponents": any(c.get("replaced") for c in res.components.values()),
                        "hasSpellCorrectedComponents": any(c.get("spellCorrected")
                                                           for c in res.components.values()),
                        "reasons": [{"code": r, "message": REASON_TEXT.get(r, r)} for r in dict.fromkeys(res.reasons)]},
            "address": {"formattedAddress": self._format(res.components), "addressComponents": comps,
                        "missingComponentTypes": missing if res.action != ACCEPT else []},
            "geocode": {"location": {"latitude": res.lat, "longitude": res.lng},
                        "plusCode": {"globalCode": encode(res.lat, res.lng)}} if res.lat is not None else None,
            "nonAddressInfo": res.parsed.noise or None,
            "codes": res.parsed.codes or None,
            "candidates": [{"formattedAddress": ", ".join(str(c[k]) for k in ("building", "number", "street", "area",
                                                                              "postcode") if c.get(k)),
                            **({"location": {"latitude": c["lat"], "longitude": c["lng"]}} if "lat" in c else {})}
                           for c in res.candidates],
            "metadata": {"regionCode": res.market, "marketClass": self.m.cls, "parser": res.parser},
        }}


    def _format(self, comps: dict[str, dict]) -> str:
        """按各市场习惯排版：12 Smith Street / Musterstraße 12；邮编在城市前（欧洲）或后。"""
        t = {k: v["text"] for k, v in comps.items()}
        unit = t.get("subpremise", "")
        unit = unit.title() if unit.isupper() and len(unit) > 2 and any(c.isalpha() for c in unit) else unit
        num, route = t.get("street_number"), t.get("route")
        pc, loc = fmt_postcode(t.get("postal_code"), self.market), t.get("locality")
        if self.market == "NL":  # 荷兰写法：Rozengracht 162A、Aalsmeerderweg 283-30、邮编 1016 NK
            if num and unit and len(unit) <= 4:
                num, unit = (num + unit if len(unit) == 1 and unit.isalpha() else f"{num}-{unit.upper()}"), ""
        if self.market == "JP":  # 〒150-0041 渋谷区神南一丁目12（从大到小连写）
            head = f"{loc or ''}{route or ''}{num or ''}"
            return " ".join(x for x in (f"〒{pc}" if pc else "", head, t.get("premise_name"), unit,
                                        t.get("plus_code")) if x)
        line = " ".join(x for x in ((num, route) if self.m.number_first else (route, num)) if x)
        if self.market == "CO" and num and route:  # Calle 72 # 8-24
            line = f"{route} # {num}"
        if self.m.postcode_first:
            tail = " ".join(x for x in (pc, loc) if x)
        elif self.market == "AU" and pc:
            tail = " ".join(x for x in (loc, AU_STATE.get(pc[:1], ""), pc) if x)
        elif self.m.state and pc:  # Toronto ON M5V 2K4
            tail = " ".join(x for x in (loc, self.m.state, pc) if x)
        else:
            tail = ", ".join(x for x in (loc, pc) if x)
        return ", ".join(x for x in (unit, t.get("premise_name"), line, tail, t.get("plus_code")) if x)


REASON_TEXT = {
    "NON_ADDRESS_INFO_EXTRACTED": "已把电话 / 邮箱 / 网址等非地址信息分离出来",
    "ONLY_LOCALITY": "只能确认到片区 / 邮编范围，找不到道路或楼宇",
    "NO_MATCH": "参考数据里找不到这个地址的任何部分",
    "STREET_SPELL_CORRECTED": "道路名有拼写错误，已按参考数据纠正",
    "STREET_TRANSLITERATED": "道路名是拉丁字母转写，已对应到阿拉伯文名称",
    "LOCATED_BY_PLUS_CODE": "按输入里的 Plus Code 定位",
    "LOCATED_BY_COORDINATES": "按输入里的经纬度定位",
    "LLM_REWRITTEN": "本地小模型改写过输入里的字段（不是原文照抄），需要用户确认",
    "LOW_CONFIDENCE": "置信度低于请求里设定的门槛（confidenceThreshold），改为请用户确认",
    "LLM_UNVERIFIED": "地址是本地小模型读出来的，这个市场没有官方地址表可以核实门牌，需要用户确认",
    "PLUS_CODE_STREET_MISMATCH": "Plus Code 的位置与所写道路不符",
    "PLUS_CODE_AREA_MISMATCH": "Plus Code 的位置不在所写片区附近",
    "ROUTE_NOT_CORROBORATED": "只验证到道路：缺少邮编与道路相互印证，或同名道路不止一条，需要用户确认",
    "STREET_PARTIAL_MATCH": "道路名只匹配上一部分（后面还有没认出的词），可能是另一条路",
    "BUILDING_SPELL_CORRECTED": "楼名是纠错后才对上的，需要用户确认",
    "LANDMARK_RELATIVE": "输入用参照物描述位置（在某楼后面 / 对面 / 附近），楼宇只是参照物",
    "BUILDING_NAME_AMBIGUOUS": "同名楼宇有多处，需要用户确认是哪一处",
    "POSTCODE_NOT_FOUND": "官方地址表里没有这个邮编",
    "POSTCODE_STREET_MISMATCH": "邮编与道路相距很远，互相矛盾",
    "POSTCODE_REPLACED": "邮编与门牌地址不符，已替换为官方邮编",
    "POSTCODE_INFERRED": "输入没有邮编，已按官方地址补全",
    "AREA_STREET_MISMATCH": "所写片区与道路位置不符",
    "BUILDING_ONLY": "只凭楼宇 / 地点名定位，没有可核对的道路",
    "STREET_INFERRED": "输入没有道路名，按邮编 + 门牌推断",
    "PREMISE_NOT_FOUND": "这条路上没有这个门牌号",
    "PREMISE_INTERPOLATED": "官方地址表里没有这个门牌，但同一条路上紧挨着的门牌在，位置按相邻门牌给出，需要用户确认门牌",
    "MISSING_PREMISE": "缺少门牌号或楼宇名",
    "AMBIGUOUS_MULTIPLE_CANDIDATES": "有多个相距较远、可信度接近的候选地址，需要用户确认",
    "UNIT_MISSING_MULTI_UNIT_BUILDING": "该门牌下有多个单元，但没有写单元号",
}


def _display(names: list[str], raw: str) -> str:
    """返回与输入同一种文字的名称（输入写英文就给英文名，写阿拉伯文 / 泰文就给当地文字）。"""
    counts = {"arabic": len(re.findall(r"[؀-ۿ]", raw)), "thai": len(re.findall(r"[฀-๿]", raw)),
              "latin": len(LATIN.findall(raw))}
    want = max(counts, key=counts.get)  # 混写时按字数多的文字（"Sheikh Zayed Rd, دبي" -> 英文）
    return next((n for n in names if _script(n) == want), names[0])


def _script(name: str) -> str:
    """名称的文字：arabic / thai / latin（只含拉丁字母）/ other（马拉雅拉姆文、中文等，不当作拉丁文）。"""
    if re.search(r"[؀-ۿ]", name):
        return "arabic"
    if re.search(r"[฀-๿]", name):
        return "thai"
    letters = [c for c in name if c.isalpha()]
    return "latin" if letters and all(LATIN.match(c) for c in letters) else "other"


LATIN = re.compile(r"[A-Za-z\u00C0-\u024F\u1E00-\u1EFF]")  # 拉丁字母（含越南文、德法重音）；不能写成 À-ỹ，那会包含印度诸文字


AU_STATE = {"2": "NSW", "3": "VIC", "4": "QLD", "5": "SA", "6": "WA", "7": "TAS", "8": "NT"}


# ---------------------------------------------------------------------------------------------- 放宽规则
_POLICY: dict | None = None


def load_policy() -> dict:
    """models/accept_policy.json：{市场: [允许直接通过的证据组合]}，由 scripts/fit_accept_policy.py 在开发集上生成。"""
    global _POLICY
    if _POLICY is None:
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parents[2] / "models" / "accept_policy.json"
        _POLICY = json.loads(path.read_text(encoding="utf-8")).get("allow", {}) if path.exists() else {}
    return _POLICY


_CORRECTION_NOTES = ("STREET_SPELL_CORRECTED", "STREET_PARTIAL_MATCH", "POSTCODE_REPLACED", "POSTCODE_NOT_FOUND",
                     "POSTCODE_STREET_MISMATCH", "AREA_STREET_MISMATCH", "STREET_INFERRED")


def policy_key_premise(h: Hypothesis) -> str | None:
    """A 类：门牌已由官方地址点确认，唯一的"纠正"是邮编被替换。"""
    notes = {n for n in h.notes if n in _CORRECTION_NOTES}
    return "PREMISE|POSTCODE_REPLACED" if notes == {"POSTCODE_REPLACED"} else None


def policy_key_route(h: Hypothesis) -> str:
    """B / C 类道路级：哪些字段相互印证 + 道路名是否唯一 + 名称怎么对上的。"""
    sp = h.street_span
    sup = ("pc" if "postcode" in h.support else "-") + ("+area" if "area" in h.support else "") + \
          ("+bldg" if "building" in h.support else "")
    return f"ROUTE|{sup}|{'u1' if sp is not None and len(sp.ids) == 1 else 'uN'}|{sp.how if sp else '-'}"


def _merge(base: Parsed, extra: Parsed) -> Parsed:
    """规则 / 机器学习的解析结果 + 模型补出的字段（只补缺的，道路两边的候选都保留）。"""
    from dataclasses import replace
    m = replace(base, streets=base.streets + [s for s in extra.streets if s.text not in {x.text for x in base.streets}],
                areas=base.areas or extra.areas, buildings=base.buildings or extra.buildings,
                number=base.number or extra.number, unit=base.unit or extra.unit,
                postcode=base.postcode or extra.postcode, parser="llm")
    m.verbatim = getattr(extra, "verbatim", True)  # type: ignore[attr-defined]
    return m


def _far(ref: MarketReference, a: Hypothesis, b: Hypothesis) -> bool:
    pa, pb = _loc(ref, a), _loc(ref, b)
    return pa is not None and pb is not None and haversine(pa[0], pa[1], pb[0], pb[1]) > 1000


def _loc(ref: MarketReference, h: Hypothesis):
    if h.point:
        return h.point["lat"], h.point["lng"]
    if h.code:
        return h.code[0], h.code[1]
    if h.building:
        return h.building["lat"], h.building["lng"]
    if h.street is not None:
        return ref.streets[h.street].lat, ref.streets[h.street].lng
    return None


def _rank(res: Result) -> tuple:
    order = {"PREMISE": 4, "PREMISE_PROXIMITY": 3, "ROUTE": 2, "LOCALITY": 1, "OTHER": 0}
    return (order[res.granularity], res.best.score if res.best else -99)
