"""没有参考库的国家（科威特、巴林、阿曼、卡塔尔、埃及、哈萨克斯坦、乌兹别克斯坦、秘鲁、多米尼加、土耳其、南非……）：
只用用户原文 + 全国地名表核对 geo 返回的门址，不依赖本方案的市场参考库。

逐字段判定与 geo_check.check 相同（CONFIRMED / CORRECTED / INFERRED / CONFLICT）：
  门牌  geo 的门牌号在原文里出现（10/26、22-53 这类复合号的任一部分也算）
  道路  geo 路名去掉类型词后的每个词都在原文里（拼写容错、阿拉伯文与拉丁转写按辅音骨架比）；编号道路的号码必须一致
  城镇  原文写的城镇 / 区（GeoNames）离 geo 坐标在城区半径内；写了却离得远 -> CONFLICT（geo 选了别的城市的同名路）
结论：门牌、道路都确认且坐标在所写城镇里 -> ACCEPT；有纠正 / 补全 -> CONFIRM；冲突、只到道路级、没写门牌 -> FIX
（geo 结果列为候选）。没有参考数据独立印证，所以"直接通过"还要求原文写了城镇、而且坐标落在那里。
"""

from __future__ import annotations

import gzip
import json
import math
import re
import uuid
from dataclasses import dataclass, field

from .coverage import norm, town_radius
from .geo_check import STREET_LEVEL_TYPES, GeoAddress, GeoCheck, parse_geo
from .noise import strip_noise
from .reference import DATA, haversine, number_key
from .geo_text import numbered_only, route_match
from .text import fold

ACCEPT, CONFIRM, FIX = "ACCEPT", "CONFIRM", "FIX"
_NUM = re.compile(r"\d+[A-Z]?(?:[/\-]\d+[A-Z]?)*")
_SEG = re.compile(r"\s*(?:[,;|\n]|\s[-–—]\s)\s*")
RANK = {"VERIFIED": 4, "PLAUSIBLE": 3, "MISSING_NUMBER": 2, "STREET_LEVEL": 1, "REJECTED": 0}


class TownIndex:
    """一个国家的城镇 / 区名索引（scripts/fetch_gazetteer.py --countries 生成的 data/markets/<国家>/gazetteer.json.gz）。"""

    def __init__(self, cc: str):
        self.cc = cc
        self.names: dict[str, list[tuple]] = {}
        src = DATA / cc / "gazetteer.json.gz"
        if not src.exists():
            return
        with gzip.open(src, "rt", encoding="utf-8") as f:
            raw = json.load(f)
        for nms, lat, lng, kind, pop, _a1 in raw["places"]:
            if kind == "A1" or (kind == "P" and 0 < pop < 1000):  # 州太大；人口不详以外的小村常与普通词同名
                continue
            # 城区半径从紧：同一都市圈里相邻的区（利马的 Lurín 与 Pachacámac）不能互相算"在所写城镇里"
            #（大城市按都市区算：约翰内斯堡、新加坡的郊区离城市中心点 20 公里以上）
            r = ((3000.0 + 2500.0 * math.log10(max(pop, 1000) / 1000) if pop < 100000 else town_radius(pop))
                 if kind == "P" else 5000.0 if kind == "X" else max(10000.0, town_radius(pop)))
            for k in {norm(n) for n in nms}:
                if len(k) >= 3 and not k.isdigit():
                    self.names.setdefault(k, []).append((lat, lng, r))

    def locality(self, text: str, lat: float, lng: float) -> str:
        """原文写的城镇 / 区包含 geo 坐标 -> CONFIRMED；写了但都离得远 -> CONFLICT；原文没有可查的城镇 -> ""。"""
        found = False
        for i, seg in enumerate(_SEG.split(text)):
            if i == 0:  # 第一段多是道路 / 楼名
                continue
            for cand in (seg, re.split(r"[/(]", seg)[0]):
                k = " ".join(t for t in norm(cand).split() if not t.isdigit())
                hits = self.names.get(k)
                if not hits:
                    continue
                found = True
                if any(haversine(lat, lng, a, b) <= r for a, b, r in hits):
                    return "CONFIRMED"
                break
        return "CONFLICT" if found else ""


_TOWNS: dict[str, TownIndex] = {}


def towns(cc: str) -> TownIndex:
    if cc not in _TOWNS:
        _TOWNS[cc] = TownIndex(cc)
    return _TOWNS[cc]


def check_free(text: str, g: GeoAddress, idx: TownIndex | None = None) -> GeoCheck:
    """不用参考库，把 geo 的门址代回原文逐字段判定。"""
    clean = strip_noise(text)[0]
    t = fold(clean)
    nums = _NUM.findall(t)
    parts = set(nums) | {p for n in nums for p in re.split(r"[/\-]", n)}
    fields: dict[str, str] = {"postal_code": ""}
    flags: list[str] = []
    gn = number_key(g.number) if g.number else ""
    if not gn or not re.search(r"\d", gn) or g.location_type in STREET_LEVEL_TYPES:
        fields["number"] = "MISSING"
    elif not nums:
        fields["number"] = "INFERRED"
    elif gn in parts:
        fields["number"] = "CONFIRMED"
    elif re.sub(r"[A-Z]+$", "", gn) in {re.sub(r"[A-Z]+$", "", p) for p in parts}:
        fields["number"] = "CORRECTED"
    else:
        fields["number"] = "CONFLICT"
    fields["route"] = route_match(g.route, clean) if g.route else "MISSING"
    if g.route and numbered_only(g.route):
        flags.append("GEO_AMBIGUOUS")  # 编号路名（شارع 18、Street 7）同一城市里有很多条：不直接通过
    fields["locality"] = idx.locality(clean, g.lat, g.lng) if idx is not None and idx.names else ""
    hard = [f for f in ("number", "route", "locality") if fields[f] == "CONFLICT"]
    if fields["number"] == "MISSING" or fields["route"] == "MISSING":
        verdict = "STREET_LEVEL"
        flags.append("GEO_STREET_LEVEL_ONLY")
    elif hard:
        verdict = "REJECTED"
        flags += [{"number": "GEO_NUMBER_CONFLICT", "route": "GEO_ROUTE_CONFLICT",
                   "locality": "AREA_STREET_MISMATCH"}[h] for h in hard]
    elif fields["number"] == "INFERRED":
        verdict = "MISSING_NUMBER"
        flags.append("GEO_NUMBER_INFERRED")
    elif fields["number"] == "CONFIRMED" and fields["route"] == "CONFIRMED" and "GEO_AMBIGUOUS" not in flags:
        verdict = "VERIFIED"
    else:
        verdict = "PLAUSIBLE"
        flags += [c for f, c in (("route", "GEO_ROUTE_CORRECTED"), ("number", "GEO_NUMBER_CORRECTED"))
                  if fields[f] == "CORRECTED"]
        flags += ["GEO_ROUTE_INFERRED"] if fields["route"] == "INFERRED" else []
    return GeoCheck(g, fields, list(dict.fromkeys(flags)), verdict, hard)


@dataclass
class FreeResult:
    market: str
    action: str
    granularity: str
    lat: float | None
    lng: float | None
    reasons: list[str]
    check: GeoCheck | None = None
    candidates: list[GeoAddress] = field(default_factory=list)


def validate_free(cc: str, text: str, geo, strictness: str = "BALANCED") -> FreeResult:
    """没有参考库的国家：只核对 geo 的门址。"""
    cc = cc.upper()
    idx = towns(cc)
    checks = [check_free(text, g, idx) for g in parse_geo(geo)]
    if not checks:
        return FreeResult(cc, FIX, "OTHER", None, None, ["NO_REFERENCE_DATA", "GEO_NO_RESULT"])
    c = max(checks, key=lambda x: RANK[x.verdict])
    g = c.geo
    reasons = ["NO_REFERENCE_DATA"] + c.flags
    if c.verdict in ("REJECTED", "STREET_LEVEL", "MISSING_NUMBER"):
        reasons += ["GEO_REJECTED"] if c.verdict != "MISSING_NUMBER" else ["MISSING_PREMISE"]
        return FreeResult(cc, FIX, "ROUTE" if c.verdict == "MISSING_NUMBER" else "OTHER", None, None, reasons, c, [g])
    ok = c.verdict == "VERIFIED" and c.fields["locality"] == "CONFIRMED" and strictness != "STRICT"
    gran = "PREMISE_PROXIMITY" if g.location_type == "RANGE_INTERPOLATED" else "PREMISE"
    return FreeResult(cc, ACCEPT if ok else CONFIRM, gran, g.lat, g.lng, reasons + (["GEO_VERIFIED"] if ok else []), c)


def to_response(res: FreeResult) -> dict:
    """与多市场引擎相同的 Google AV 风格响应（没有参考库：组件只来自 geo，确认级别按逐字段判定）。"""
    from .engine import REASON_TEXT
    level = {"CONFIRMED": "CONFIRMED", "CORRECTED": "UNCONFIRMED_BUT_PLAUSIBLE", "INFERRED": "UNCONFIRMED_BUT_PLAUSIBLE",
             "CONFLICT": "UNCONFIRMED_AND_SUSPICIOUS", "MISSING": "UNCONFIRMED_BUT_PLAUSIBLE", "": "UNCONFIRMED_BUT_PLAUSIBLE"}
    comps = []
    g = res.check.geo if res.check is not None and res.action != FIX else None
    if g is not None:
        f = res.check.fields
        for ctype, val, key in (("street_number", g.number, "number"), ("route", g.route, "route"),
                                ("locality", g.localities[0] if g.localities else "", "locality")):
            if val:
                comps.append({"componentType": ctype, "componentName": {"text": val}, "confirmationLevel": level[f[key]],
                              **({"inferred": True} if f[key] == "INFERRED" else {}),
                              **({"spellCorrected": True} if f[key] == "CORRECTED" else {})})
    return {"responseId": str(uuid.uuid4()), "result": {
        "verdict": {"possibleNextAction": res.action, "validationGranularity": res.granularity,
                    "geocodeGranularity": res.granularity, "addressComplete": res.action == ACCEPT,
                    "hasUnconfirmedComponents": any(c["confirmationLevel"] != "CONFIRMED" for c in comps) or not comps,
                    "reasons": [{"code": r, "message": REASON_TEXT.get(r, r)} for r in dict.fromkeys(res.reasons)]},
        "address": {"formattedAddress": g.formatted if g is not None else "", "addressComponents": comps},
        "geocode": {"location": {"latitude": res.lat, "longitude": res.lng}} if res.lat is not None else None,
        "candidates": [{"formattedAddress": c.formatted, "location": {"latitude": c.lat, "longitude": c.lng}}
                       for c in res.candidates],
        "metadata": {"regionCode": res.market, "marketClass": "none", "parser": "geo-only"},
    }}
