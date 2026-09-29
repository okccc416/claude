"""校验主流程：解析 → 多路召回 → 假设打分 → 结论决策 → 输出（字段语义对齐 Google AV，并带扩展字段）。

结论决策刻意写成可读的规则树而不是黑盒打分：每个分支对应一个原因码，
方便产品、客服和客户理解"为什么是这个结论"，也方便用评测集逐条定位问题。
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field, replace

from rapidfuzz import fuzz

from .noise import NoiseResult, strip_noise
from .normalize import canon_tokens, clean_text, match_key, strip_punct, title_case
from .parser import BLOCK_RE, ParsedAddress, parse
from .reference import Entity, ReferenceDB, RoadMatch

ACCEPT, CONFIRM, FIX, ADD_SUB = "ACCEPT", "CONFIRM", "FIX", "CONFIRM_ADD_SUBPREMISES"
_ACTION_LETTER = {ACCEPT: "A", CONFIRM: "C", FIX: "F", ADD_SUB: "S"}
_GRAN_DIGIT = {"SUB_PREMISE": 5, "PREMISE": 4, "ROUTE": 3, "OTHER": 0}

_REASON_TEXT = {
    "POSTCODE_INFERRED": "邮编由系统根据楼栋号和道路补全",
    "POSTCODE_LEADING_ZERO_RESTORED": "邮编缺少前导 0（常见于表格软件），已补回",
    "POSTCODE_NOT_FOUND": "邮编不存在，已按楼栋号和道路替换",
    "POSTCODE_STREET_MISMATCH": "邮编与楼栋号 / 道路不一致",
    "POSTCODE_BLOCK_CONFLICT": "邮编与楼栋号指向同一道路上的不同楼栋，无法判断哪个输错",
    "POSTCODE_ONLY": "仅凭邮编确定地址，楼栋号和道路由系统补全",
    "BLOCK_INFERRED": "楼栋号由系统补全",
    "BLOCK_REPLACED_BY_POSTCODE": "楼栋号在该道路上不存在，已按邮编和道路替换",
    "STREET_SPELL_CORRECTED": "道路名拼写已纠正",
    "STREET_INFERRED": "道路名由系统补全",
    "STREET_REPLACED": "道路名与邮编 / 楼栋号不一致，已替换",
    "PREMISE_NOT_FOUND": "该道路上不存在此楼栋号",
    "PREMISE_UNVERIFIED_LOW_COVERAGE": "楼栋号查不到，但参考数据可能不完整，请用户确认",
    "MISSING_PREMISE": "缺少楼栋号，且该道路上有多栋楼",
    "AMBIGUOUS_MULTIPLE_CANDIDATES": "存在多个候选地址，无法区分",
    "BUILDING_NAME_ONLY": "仅凭楼宇名确定地址",
    "NO_MATCH": "无法匹配到任何已知地址",
    "UNRESOLVED_TOKENS": "存在无法解析的输入片段",
    "UNIT_FORMAT_INVALID": "单元号格式不合法",
    "UNIT_FLOOR_EXCEEDS_BUILDING": "单元楼层超过该楼栋最高层",
    "UNIT_MISSING_MULTI_UNIT_BUILDING": "多单元住宅楼缺少单元号",
    "NON_ADDRESS_INFO_EXTRACTED": "已从输入中分离出电话 / 收件人 / 备注等非地址信息（见 nonAddressInfo）",
}


@dataclass
class Config:
    strictness: str = "BALANCED"  # STRICT / BALANCED / LENIENT
    fuzzy_road: bool = True  # 消融开关：道路名拼写纠错
    consistency_check: bool = True  # 消融开关：邮编与楼栋/道路交叉校验
    building_route: bool = True  # 消融开关：楼宇名召回
    assume_complete: bool = True  # 参考库在该区域是否完整；False 时"查不到"只判"无法确认"
    strip_noise: bool = True  # 消融开关：剥离电话 / 收件人 / 备注等业务噪声


@dataclass
class Hypothesis:
    blk: str | None
    blk_marked: bool
    road: RoadMatch | None
    tokens: list[str]
    br: list[int]
    orig_tokens: list[str] = field(default_factory=list)
    steal: bool = False  # 该楼栋号其实是某条真实道路名的一部分（如 TAMPINES AVE 7 的 7）

    @property
    def leftover(self) -> list[str]:
        if self.road is None:
            return list(self.tokens)
        return self.tokens[: self.road.start] + self.tokens[self.road.end:]


@dataclass
class Result:
    action: str
    entity: Entity | None
    parsed: ParsedAddress
    reasons: list[str] = field(default_factory=list)
    status: dict[str, str] = field(default_factory=dict)  # 组件 -> confirmed/corrected/inferred/replaced/suspicious/plausible
    unresolved: list[str] = field(default_factory=list)
    candidates: list[int] = field(default_factory=list)
    road: RoadMatch | None = None
    blk: str | None = None
    tokens: list[str] = field(default_factory=list)  # 当前假设使用的 token（不含楼栋号）
    orig_tokens: list[str] = field(default_factory=list)
    building_confirmed: str | None = None
    noise: NoiseResult | None = None


class Validator:
    def __init__(self, db: ReferenceDB, config: Config | None = None):
        self.db = db
        self.config = config or Config()

    # ------------------------------------------------------------------ 主入口
    def validate(self, raw: str, strictness: str | None = None) -> Result:
        cfg = self.config if strictness is None else replace(self.config, strictness=strictness)
        noise = strip_noise(raw, self._address_like) if cfg.strip_noise else None
        res = self._validate_text(noise.text if noise else raw, cfg)
        if noise and noise.removed_any:
            if res.action == FIX:
                # 剥噪声剥过头（如把真实楼宇名当成公司名删掉）时，用原文再试一次
                alt = self._validate_text(raw, cfg)
                if alt.action != FIX:
                    return alt
            res.noise = noise
            res.reasons.append("NON_ADDRESS_INFO_EXTRACTED")
        return res

    def _address_like(self, segment: str) -> bool:
        """这段文字能否在参考库里命中道路或楼宇名（用于防止把地址当噪声删掉）。"""
        toks = canon_tokens(strip_punct(clean_text(segment)).split())
        if not toks:
            return False
        if self.db.find_roads(toks, fuzzy=False) or self.db.exact_building(toks):
            return True
        return 0 < len(self.db.find_building_entities(toks, fuzzy=False)) <= 5

    def _validate_text(self, raw: str, cfg: Config) -> Result:
        p = parse(raw)
        P = list(self.db.by_postal.get(p.postal, [])) if p.postal else []
        # 多套 token 一起试：原样的、纠正路型词拼写的、逐词拼写纠错的，以及粘连写法的另一种切分。
        # 纠错可能误伤（如 COUSE -> CLOSE），所以不直接替换，而是交给打分裁决
        variants: list[tuple[list[str], list[str]]] = []
        for base, orig in ((p.tokens, p.orig_tokens), (p.alt_tokens, p.alt_tokens)):
            if not base:
                continue
            cands = [base]
            if cfg.fuzzy_road:
                fixed = self.db.fix_type_typos(base)
                cands += [fixed, self.db.spell_fix(fixed)]
            for c in cands:
                if all(c != v[0] for v in variants):
                    variants.append((c, orig))
        if not variants:
            variants = [(p.tokens, p.orig_tokens)]
        hyps = [h for toks, orig in variants for h in self._hypotheses(p, toks, orig, cfg)]
        if cfg.building_route and p.block_marked and p.all_tokens != p.tokens:
            # 楼宇名本身带 "BLK 652" 之类字样时，整串当楼宇名再试一次
            hyps.append(Hypothesis(None, False, None, p.all_tokens, [], p.all_tokens))
        pset = set(P)
        p_blks = {self.db.entities[e].blk for e in P}
        p_roads = {self.db.entities[e].road_key for e in P}
        bcache: dict[tuple[str, ...], list[int]] = {}

        def exact_unique_building(h: Hypothesis) -> bool:
            # 整串恰好是某个唯一楼宇名（且不是某条路的名字），并且与楼栋号不矛盾：视为强证据
            if h.road is not None or not cfg.building_route or not h.tokens or " ".join(h.tokens) in self.db.by_road:
                return False
            ids = self.db.exact_building(h.tokens, p.country_suffix, p.country_prefix)
            return len(ids) == 1 and (h.blk is None or self.db.entities[ids[0]].blk == h.blk)

        def building_strength(h: Hypothesis) -> int:
            # 只对"没识别出道路"的假设计算：词全部命中且唯一=2，命中少量候选=1；与楼栋号矛盾则降级
            if h.road is not None or not cfg.building_route or not h.tokens:
                return 0
            key = tuple(h.tokens)
            if key not in bcache:
                bcache[key] = self.db.find_building_entities(h.tokens, fuzzy=False, suffix=p.country_suffix)
            ids = bcache[key]
            if h.blk and ids and all(self.db.entities[i].blk != h.blk for i in ids):
                return 0
            return 2 if len(ids) == 1 else 1 if 1 < len(ids) <= 5 else 0

        # 同一切分下，道路片段被另一个更长的道路片段完全包含 => 被支配（如 KEPPEL BAY ⊂ KEPPEL BAY VIEW）
        spans: dict[tuple, list[tuple[int, int]]] = defaultdict(list)
        for x in hyps:
            if x.road:
                spans[(x.blk, tuple(x.tokens))].append((x.road.start, x.road.end))

        def dominated(h: Hypothesis) -> bool:
            if not h.road:
                return False
            s0, e0 = h.road.start, h.road.end
            return any(s1 <= s0 and e1 >= e0 and (e1 - s1) > (e0 - s0) for s1, e1 in spans[(h.blk, tuple(h.tokens))])

        def prefix(h: Hypothesis):
            br = set(h.br)
            exact_b = exact_unique_building(h)
            return (
                2 if br & pset else 0,  # 邮编 + 楼栋号 + 道路三者一致
                0 if h.steal else 1,
                0 if dominated(h) else 1,
                # 两个独立字段互相印证：楼栋号+道路 / 邮编+楼栋号（道路没认出） / 唯一楼宇名
                1 if br or exact_b or (h.road is None and h.blk and h.blk in p_blks) else 0,
                len(h.tokens) if exact_b else (h.road.end - h.road.start) if h.road else 0,
                1 if h.road and h.road.key in p_roads else 0,
                1 if h.road and h.road.exact else 0,
            )

        def rest(h: Hypothesis):
            return (
                building_strength(h),
                h.road.score if h.road else 0,
                (h.road.end - h.road.start) if h.road else 0,
                1 if h.blk else 0,
            )

        # 先用廉价的前缀排序，只对并列最优的假设再算楼宇名等较贵的特征
        best = max(prefix(x) for x in hyps)
        h = max((x for x in hyps if prefix(x) == best), key=rest)
        return self._decide(p, P, h, cfg)

    def _hypotheses(self, p: ParsedAddress, T: list[str], O: list[str], cfg: Config):
        """楼栋号有歧义时枚举所有切分方式，每种切分再配若干道路候选。"""
        opts: list[tuple[str | None, bool, int | None]] = []
        if p.block_marked:
            opts.append((p.block_marked, True, None))
        else:
            opts += [(t, False, idx) for idx, t in enumerate(T) if BLOCK_RE.match(t)]
            opts.append((None, False, None))
        # 不拆楼栋号时能精确命中的道路所覆盖的 token：拆走其中的数字当楼栋号属于"偷"路名
        exact_cover = {i for r in self.db.find_roads(T, fuzzy=False) for i in range(r.start, r.end)}
        for blk, marked, idx in opts:
            toks = T if idx is None else T[:idx] + T[idx + 1:]
            orig = O if idx is None else O[:idx] + O[idx + 1:]
            for r in [*self.db.find_roads(toks, fuzzy=cfg.fuzzy_road), None]:
                if r is not None and r.exact and toks[r.start:r.end] != orig[r.start:r.end]:
                    r = RoadMatch(r.key, r.start, r.end, 95.0, False)  # 路型词被纠错过
                br = list(self.db.by_blk_road.get((blk, r.key), [])) if (blk and r) else []
                yield Hypothesis(blk, marked, r, toks, br, orig, steal=idx is not None and idx in exact_cover)

    # ------------------------------------------------------------------ 决策
    def _pick(self, eids: list[int], leftover: list[str], cfg: Config) -> int | None:
        """多个候选时用楼宇名消歧。"""
        if len(eids) == 1:
            return eids[0]
        if leftover and cfg.building_route:
            text = " ".join(leftover)
            hits = [e for e in eids if self._building_score(self.db.entities[e], text) >= 90]
            if len(hits) == 1:
                return hits[0]
        return None

    @staticmethod
    def _building_score(e: Entity, text: str) -> float:
        return max((fuzz.token_set_ratio(match_key(b), text) for b in e.buildings), default=0.0)

    def _decide(self, p: ParsedAddress, P: list[int], h: Hypothesis, cfg: Config) -> Result:
        db, road, blk = self.db, h.road, h.blk
        leftover = h.leftover
        res = Result(action=FIX, entity=None, parsed=p, road=road, blk=blk, tokens=h.tokens,
                     orig_tokens=h.orig_tokens)
        pset = set(P)
        eid: int | None = None
        poi_only = False

        if P and not cfg.consistency_check:
            # 消融：邮编优先、不做交叉校验（很多"查邮编即可"方案的做法）
            eid = self._pick(P, leftover, cfg)
            eid = P[0] if eid is None else eid
        elif h.br:
            inter = [e for e in h.br if e in pset]
            if inter:
                eid = self._pick(inter, leftover, cfg)
                eid = inter[0] if eid is None else eid
            elif P:
                same_road = [e for e in P if db.entities[e].road_key == road.key]
                if same_road:
                    res.reasons.append("POSTCODE_BLOCK_CONFLICT")
                    res.candidates = h.br + same_road
                else:
                    eid = self._pick(h.br, leftover, cfg)
                    if eid is None:
                        res.reasons.append("AMBIGUOUS_MULTIPLE_CANDIDATES")
                        res.candidates = list(h.br)
                    else:
                        res.reasons.append("POSTCODE_STREET_MISMATCH")
            else:
                eid = self._pick(h.br, leftover, cfg)
                if eid is None:
                    res.reasons.append("AMBIGUOUS_MULTIPLE_CANDIDATES")
                    res.candidates = list(h.br)
                elif p.postal:
                    res.reasons.append("POSTCODE_NOT_FOUND")
        elif P:
            if road is None and blk is None:
                eid = self._pick(P, leftover, cfg)
                if eid is None:
                    res.reasons.append("AMBIGUOUS_MULTIPLE_CANDIDATES")
                    res.candidates = list(P)
                else:
                    res.reasons.append("POSTCODE_ONLY")
            elif road is not None:
                same_road = [e for e in P if db.entities[e].road_key == road.key]
                if same_road and blk is None:
                    eid = self._pick(same_road, leftover, cfg)
                    if eid is None:
                        res.reasons.append("AMBIGUOUS_MULTIPLE_CANDIDATES")
                        res.candidates = same_road
                elif same_road and len(same_road) == 1 and cfg.strictness != "STRICT":
                    eid = same_road[0]
                    res.reasons.append("BLOCK_REPLACED_BY_POSTCODE")
                else:
                    res.reasons.append("POSTCODE_STREET_MISMATCH")
                    res.candidates = P + list(db.by_blk_road.get((blk, road.key), []))
            else:  # 有楼栋号、没识别出道路：邮编 + 楼栋号一致即可确定
                hit = [e for e in P if db.entities[e].blk == blk]
                if len(hit) == 1:
                    eid = hit[0]
                else:
                    res.reasons.append("POSTCODE_STREET_MISMATCH")
                    res.candidates = list(P)
        elif road is not None:
            on_road = db.by_road[road.key]
            if blk is not None:
                if cfg.assume_complete:
                    res.reasons.append("PREMISE_NOT_FOUND")
                    res.candidates = self._nearest_blocks(road.key, blk)
                else:
                    res.reasons.append("PREMISE_UNVERIFIED_LOW_COVERAGE")
                    res.action = CONFIRM
                    res.status = {"premise": "plausible",
                                  "route": "confirmed" if road.exact else "corrected",
                                  "postal": "plausible" if p.postal else "missing"}
                    return res
            else:
                eid = self._pick(on_road, leftover, cfg)
                if eid is None and cfg.building_route and leftover:
                    # 楼宇名本身包含道路名的情况（如 DBS BEDOK CENTRAL BRANCH）
                    on = set(on_road)
                    hit = [e for e in db.find_building_entities(h.tokens, fuzzy=False, suffix=p.country_suffix)
                           if e in on]
                    eid = hit[0] if len(hit) == 1 else None
                    if eid is not None:
                        leftover = h.tokens
                if eid is None:
                    res.reasons.append("MISSING_PREMISE")
                    res.candidates = on_road[:5]
        else:
            eids = []
            if cfg.building_route and leftover:
                eids = (db.exact_building(leftover, p.country_suffix, p.country_prefix)
                        or db.find_building_entities(leftover, suffix=p.country_suffix))
            if blk:
                eids = [e for e in eids if db.entities[e].blk == blk] or eids
            if len(eids) == 1:
                eid = eids[0]
                poi_only = True
                res.reasons.append("BUILDING_NAME_ONLY")
            elif eids:
                res.reasons.append("AMBIGUOUS_MULTIPLE_CANDIDATES")
                res.candidates = eids[:5]
            else:
                res.reasons.append("NO_MATCH")

        if eid is None:
            res.action = FIX
            return res

        e = db.entities[eid]
        res.entity = e
        st = res.status
        # 楼栋号
        if blk is None:
            st["premise"] = "inferred"
            if "POSTCODE_ONLY" not in res.reasons and not poi_only:
                res.reasons.append("BLOCK_INFERRED")
        else:
            st["premise"] = "confirmed" if blk == e.blk else "replaced"
        # 道路
        typed = db.find_roads(leftover, fuzzy=False) if road is None and leftover else []
        if typed and typed[0].key != e.road_key:
            # 用户写了一条真实存在的路，但邮编 + 楼栋号指向另一条路：属于"替换"而不是"补全"
            st["route"] = "replaced"
            res.reasons.append("STREET_REPLACED")
            leftover = leftover[: typed[0].start] + leftover[typed[0].end:]
        elif road is None:
            st["route"] = "inferred"
            if "POSTCODE_ONLY" not in res.reasons and not poi_only:
                res.reasons.append("STREET_INFERRED")
        elif road.key == e.road_key:
            st["route"] = "confirmed" if road.exact else "corrected"
            if not road.exact:
                res.reasons.append("STREET_SPELL_CORRECTED")
        else:
            st["route"] = "replaced"
            res.reasons.append("STREET_REPLACED")
        # 邮编
        if p.postal is None:
            st["postal"] = "inferred"
            res.reasons.append("POSTCODE_INFERRED")
        elif p.postal == e.postal:
            st["postal"] = "confirmed"
            if p.postal_leading_zero_restored:
                res.reasons.append("POSTCODE_LEADING_ZERO_RESTORED")
        else:
            st["postal"] = "replaced"
        # 楼宇名 / 其余片段
        if leftover:
            text = " ".join(leftover)
            if e.buildings and self._building_score(e, text) >= 90:
                res.building_confirmed = max(
                    e.buildings, key=lambda b: (fuzz.token_set_ratio(match_key(b), text), fuzz.ratio(match_key(b), text)))
            elif not (poi_only and self._building_score(e, text) >= 80):
                res.unresolved = leftover
                res.reasons.append("UNRESOLVED_TOKENS")
        # 单元号
        unit_suspicious = False
        if p.unit:
            max_floor = db.max_floor_by_postal.get(e.postal)
            floor = p.unit_floor.lstrip("B")
            if max_floor is not None and not p.unit_floor.startswith("B") and int(floor) > max_floor:
                st["subpremise"] = "suspicious"
                res.reasons.append("UNIT_FLOOR_EXCEEDS_BUILDING")
                unit_suspicious = True
            else:
                st["subpremise"] = "plausible"
        elif p.unit_raw:
            res.unresolved.append(p.unit_raw)
            res.reasons.append("UNIT_FORMAT_INVALID")

        res.action = self._action(st, res, poi_only, unit_suspicious, cfg)
        if res.action in (ACCEPT, CONFIRM) and not p.unit and e.postal in db.max_floor_by_postal:
            # 有楼栋属性数据（如 HDB 楼栋表）即视为多单元住宅楼
            res.action = ADD_SUB
            res.reasons.append("UNIT_MISSING_MULTI_UNIT_BUILDING")
        return res

    @staticmethod
    def _action(st: dict, res: Result, poi_only: bool, unit_suspicious: bool, cfg: Config) -> str:
        if unit_suspicious:
            return FIX
        vals = set(st.values())
        replaced = "replaced" in vals
        inferred = "inferred" in vals
        corrected = "corrected" in vals
        unresolved = bool(res.unresolved)
        unit_plausible = st.get("subpremise") == "plausible"
        if cfg.strictness == "STRICT":
            needs = replaced or inferred or corrected or unresolved or poi_only or unit_plausible
        elif cfg.strictness == "LENIENT":
            needs = replaced or unresolved or poi_only
        else:
            needs = replaced or inferred or corrected or unresolved or poi_only
        return CONFIRM if needs else ACCEPT

    def _nearest_blocks(self, road_key: str, blk: str, k: int = 3) -> list[int]:
        ids = self.db.by_road[road_key]
        num = int("".join(c for c in blk if c.isdigit()) or 0)

        def dist(i: int) -> int:
            b = self.db.entities[i].blk
            return abs(int("".join(c for c in b if c.isdigit()) or 0) - num)

        return sorted(ids, key=dist)[:k]

    # ------------------------------------------------------------------ 输出
    def to_response(self, res: Result) -> dict:
        return build_response(self.db, res)


def _format_address(e: Entity, unit: str | None, building: str | None) -> str:
    parts = [f"{e.blk} {title_case(e.road)}"]
    if unit:
        parts.append(unit)
    if building:
        parts.append(title_case(building))
    parts.append(f"Singapore {e.postal}")
    return ", ".join(parts)


_LEVEL = {
    "confirmed": "CONFIRMED", "corrected": "CONFIRMED", "inferred": "CONFIRMED",
    "replaced": "CONFIRMED", "plausible": "UNCONFIRMED_BUT_PLAUSIBLE",
    "suspicious": "UNCONFIRMED_AND_SUSPICIOUS", "missing": "UNCONFIRMED_BUT_PLAUSIBLE",
}


def build_response(db: ReferenceDB, res: Result) -> dict:
    p, e, st = res.parsed, res.entity, res.status
    road_text = title_case(db.road_display[res.road.key]) if res.road else None

    # 没有确定地址时，按原因码推断各组件状态：道路存在就是存在，可疑的是楼栋号 / 邮编
    conflict = {"POSTCODE_BLOCK_CONFLICT", "POSTCODE_STREET_MISMATCH"} & set(res.reasons)
    fallback = {
        "route": ("confirmed" if res.road.exact else "corrected") if res.road else "plausible",
        "premise": "suspicious" if conflict or "PREMISE_NOT_FOUND" in res.reasons else "plausible",
        "postal": "suspicious" if conflict else "plausible",
        "subpremise": "plausible",
    }

    def comp(ctype: str, text: str | None, key: str, original: str | None = None) -> dict | None:
        if text is None:
            return None
        s = st.get(key) or fallback.get(key, "plausible")
        c = {"componentType": ctype, "componentName": {"text": text, "languageCode": "en"},
             "confirmationLevel": _LEVEL.get(s, "UNCONFIRMED_BUT_PLAUSIBLE")}
        if s == "inferred":
            c["inferred"] = True
        if s == "replaced":
            c["replaced"] = True
        if s == "corrected":
            c["spellCorrected"] = True
        if original and match_key(original) != match_key(text):
            c["originalText"] = original
        return c

    road_orig = " ".join(res.orig_tokens[res.road.start:res.road.end]) if res.road else None
    if e is not None:
        comps = [
            comp("premise", e.blk, "premise", res.blk),
            comp("route", title_case(e.road), "route", road_orig),
            comp("postal_code", e.postal, "postal", p.postal),
            comp("subpremise", p.unit, "subpremise"),
        ]
        if res.building_confirmed:
            comps.append({"componentType": "premise_name",
                          "componentName": {"text": title_case(res.building_confirmed), "languageCode": "en"},
                          "confirmationLevel": "CONFIRMED"})
        formatted = _format_address(e, p.unit, res.building_confirmed or e.primary_building)
        location = {"latitude": e.lat, "longitude": e.lng}
        geo_gran = "PREMISE"
    else:
        comps = [
            comp("premise", res.blk, "premise"),
            comp("route", road_text, "route", road_orig),
            comp("postal_code", p.postal, "postal"),
            comp("subpremise", p.unit, "subpremise"),
        ]
        parts = [" ".join(x for x in (res.blk, road_text) if x)] if (res.blk or road_text) else []
        if p.unit:
            parts.append(p.unit)
        if p.postal:
            parts.append(f"Singapore {p.postal}")
        formatted = ", ".join(x for x in parts if x) or None
        if res.road:
            lat, lng = db.road_centroid(res.road.key)
            location, geo_gran = {"latitude": lat, "longitude": lng}, "ROUTE"
        else:
            location, geo_gran = None, "OTHER"
    comps = [c for c in comps if c]

    input_gran = ("SUB_PREMISE" if p.unit else "PREMISE" if (p.block_marked or res.blk or p.postal)
                  else "ROUTE" if res.road else "OTHER")
    if e is not None:
        val_gran = "PREMISE"
        pre_gran = ("PREMISE" if all(st.get(k) == "confirmed" for k in ("premise", "route"))
                    or (st.get("postal") == "confirmed") else "ROUTE" if st.get("route") == "confirmed" else "OTHER")
    else:
        val_gran = "ROUTE" if res.road else "OTHER"
        pre_gran = "ROUTE" if res.road and res.road.exact else "OTHER"

    vals = list(st.values())
    change = 100 - 30 * vals.count("replaced") - 10 * vals.count("inferred")
    if st.get("route") == "corrected" and res.road:
        change -= round(100 - res.road.score)
    change = max(0, change)
    code = f"{_ACTION_LETTER[res.action]}{_GRAN_DIGIT[val_gran]}{_GRAN_DIGIT[pre_gran]}-{change:03d}"

    missing = []
    if e is None:
        if not res.blk:
            missing.append("premise")
        if not res.road:
            missing.append("route")
        if not p.postal:
            missing.append("postal_code")

    return {
        "responseId": str(uuid.uuid4()),
        "result": {
            "verdict": {
                "inputGranularity": input_gran,
                "validationGranularity": val_gran,
                "preCorrectionGranularity": pre_gran,
                "geocodeGranularity": geo_gran,
                "addressComplete": res.action == ACCEPT,
                "hasUnconfirmedComponents": any(v in ("plausible", "suspicious", "missing") for v in vals)
                or (e is None),
                "hasInferredComponents": "inferred" in vals,
                "hasReplacedComponents": "replaced" in vals,
                "hasSpellCorrectedComponents": "corrected" in vals,
                "possibleNextAction": res.action,
                "changeScore": change,
                "verificationCode": code,
                "reasons": [{"code": r, "message": _REASON_TEXT.get(r, r)} for r in res.reasons],
            },
            "address": {
                "formattedAddress": formatted,
                "addressComponents": comps,
                "missingComponentTypes": missing,
                "unresolvedTokens": res.unresolved,
            },
            "geocode": {"location": location} if location else None,
            "metadata": {"buildingNames": [title_case(b) for b in e.buildings]} if e else None,
            "nonAddressInfo": res.noise.as_dict() if res.noise else None,
            "candidates": [
                {"formattedAddress": _format_address(db.entities[i], None, db.entities[i].primary_building),
                 "location": {"latitude": db.entities[i].lat, "longitude": db.entities[i].lng}}
                for i in res.candidates[:5]
            ],
        },
    }

