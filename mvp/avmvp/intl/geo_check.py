"""geo 服务结果核对：用户输入 + geo 返回的标准门址（与 Google 地理编码同样的分字段地址 + 坐标）-> 逐字段判定 + 结论。

geo 不管对错都会给一条门址，线上没有标准答案。判断它对不对不需要标准答案：把 geo 的门址代回用户原文和参考数据，
看是否自洽（同"把解代回方程"）。

逐字段判定（geo 门址的每个字段在用户原文里……）：
  CONFIRMED  出现了，而且一样（统一写法后比较；去类型词、参考库里的别名也算）
  CORRECTED  出现了但写法不同（拼错、少写几个词、门牌少了字母）
  INFERRED   用户没写，是 geo 补出来的
  CONFLICT   用户写了一个不同的值（门牌 1877、geo 给 1883；用户写的是另一条路 / 另一种类型的路）
另外几项独立检查：所写邮编的中心离 geo 坐标太远；所写片区不包含 geo 坐标；同名道路在别处也有这个门牌而输入没法区分；
geo 只定位到道路 / 区域级（location_type 不是 ROOFTOP）。

结论：
  门牌、道路都确认，邮编 / 片区不矛盾，没有同名歧义        -> ACCEPT，用 geo 的门址和坐标（GEO_VERIFIED）
  门牌确认，但道路纠正 / 补全、邮编被替换、片区不符、有歧义   -> CONFIRM，说明改了什么
  用户没写门牌                                           -> FIX（geo 补出来的门牌不能当真）
  门牌 / 道路冲突、邮编中心太远                           -> geo 多半解析错了：用本引擎重新召回裁决，geo 结果作为候选
  geo 没有结果                                           -> 本引擎
本引擎的结论同时算出来（几毫秒）用来互相印证：位置一致则采用、并沿用本引擎校准过的置信度；
都自洽但相距很远（同名道路各选了一条）时请用户确认并给出两边的候选。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from .coverage import gazetteer, locality_check
from .engine import ACCEPT, ADD_SUB, CONFIRM, FIX, Engine, Hypothesis, Result, dist_to_street
from .geo_text import numbered_only, route_match
from .reference import haversine, number_key
from .text import core_key, key, norm_postcode, postcode_prefix, type_words

LOCALITY_TYPES = ("locality", "sublocality", "sublocality_level_1", "sublocality_level_2", "postal_town",
                  "neighborhood", "administrative_area_level_2", "administrative_area_level_3")
STREET_LEVEL_TYPES = ("GEOMETRIC_CENTER", "APPROXIMATE")
AGREE_M, DISAGREE_M, ELSEWHERE_M = 250.0, 1000.0, 2000.0
NATIONAL_PC_FAR_M = 10000.0  # 全国邮编表的邮编位置离 geo 坐标超过这个距离：二者必有一错
FINE_PC = {"GB", "IE", "SE", "HU", "AR"}  # 没有官方地址表、但邮编细的市场（其余只用 A 类市场的全国邮编表）


@dataclass
class GeoAddress:
    number: str = ""
    route: str = ""
    subpremise: str = ""
    premise: str = ""
    postal_code: str = ""
    localities: list[str] = field(default_factory=list)
    lat: float | None = None
    lng: float | None = None
    location_type: str = ""
    id: str = ""
    formatted: str = ""


def parse_geo(obj) -> list[GeoAddress]:
    """geo 服务的返回 -> GeoAddress 列表。接受 Google 地理编码响应（{"results": [...]}）、单条结果、结果列表，
    组件既可以是 Geocoding 的 long_name / types，也可以是 Address Validation 的 componentName.text / componentType；
    也接受扁平字段（street_number、route、postal_code、locality、lat、lng …），以及高德海外地理编码的响应
    （{"geocodes": [{"formatted_address", "street", "number", "location": "经度,纬度", …}]}，JSON 字符串也行）。"""
    if not obj:
        return []
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except ValueError:
            return []
    if isinstance(obj, dict) and "results" in obj:
        obj = obj["results"]
    if isinstance(obj, dict) and "geocodes" in obj:
        return [g for g in (_amap(x) for x in obj["geocodes"] or [] if isinstance(x, dict)) if g is not None]
    out = []
    for it in obj if isinstance(obj, list) else [obj]:
        if not isinstance(it, dict):
            continue
        if "formatted_address" in it and isinstance(it.get("location"), str) and "," in it["location"]:
            g = _amap(it)
            if g is not None:
                out.append(g)
            continue
        g = GeoAddress()
        comps = it.get("address_components") or it.get("addressComponents")
        if comps:
            for c in comps:
                types = c.get("types") or ([c["componentType"]] if c.get("componentType") else [])
                name = (c.get("long_name") or c.get("longText") or (c.get("componentName") or {}).get("text")
                        or c.get("short_name") or c.get("shortText") or "")
                _put(g, types, str(name))
        else:
            for k, v in it.items():
                if isinstance(v, (str, int, float)) and not isinstance(v, bool):
                    _put(g, [k], str(v))
        geom = it.get("geometry") or {}
        loc = geom.get("location") or it.get("location") or (it.get("geocode") or {}).get("location") or {}
        lat = loc.get("lat", loc.get("latitude", it.get("lat", it.get("latitude"))))
        lng = loc.get("lng", loc.get("longitude", it.get("lng", it.get("longitude"))))
        g.lat, g.lng = (float(lat), float(lng)) if lat is not None and lng is not None else (None, None)
        g.location_type = str(geom.get("location_type") or it.get("location_type") or it.get("locationType") or "")
        g.id = str(it.get("place_id") or it.get("placeId") or it.get("id") or "")
        g.formatted = str(it.get("formatted_address") or it.get("formattedAddress") or "")
        if (g.route or g.number) and g.lat is not None:
            out.append(g)
    return out


AMAP_LEVEL = {"门牌号": "ROOFTOP", "兴趣点": "ROOFTOP", "单元号": "ROOFTOP", "楼栋": "ROOFTOP",
              "道路": "GEOMETRIC_CENTER", "道路交叉路口": "GEOMETRIC_CENTER"}


def _amap(it: dict) -> GeoAddress | None:
    """高德海外地理编码的一条结果。它的 street / number 常拆错：门牌号字段里是类型词、门牌号混进了 street
    （ULICA / 1 MAJA 3、CALLE / 46D 22、Грузинская / улица 2）——这时按 formatted_address 重新拆：末尾的数字是门牌。"""
    def txt(v) -> str:
        if not isinstance(v, str):
            return ""
        if "Ã" in v or "Â" in v:  # UTF-8 被当成 Latin-1 解码的乱码（Avenida MÃ©xico）：还原
            try:
                return v.encode("latin-1").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                return v
        return v
    loc = txt(it.get("location"))
    if "," not in loc:
        return None
    lng, lat = (float(x) for x in loc.split(",")[:2])
    fa, num, street = txt(it.get("formatted_address")).strip(), txt(it.get("number")).strip(), txt(it.get("street")).strip()
    fa_main = fa.split(",")[0].strip()  # 逗号后面是单元 / 楼栋（AVENIDA JOAO FRANCESCHI 2101, BLOCO 2, APTO 303）
    street = street.split(",")[0].strip()
    num = num.replace("_", "/")
    if num and not re.search(r"\d", num):
        toks = fa_main.replace("_", "/").split()
        house = re.compile(r"^\d+[A-Za-z]?(?:[/\-]\w+)?$")
        if len(toks) >= 3 and house.match(toks[-1]) and house.match(toks[-2]):  # Baron Ruzettelaan 29 0401：后一个是信箱号
            num, street = toks[-2], " ".join(toks[:-2])
        elif len(toks) >= 2 and house.match(toks[-1]):
            num, street = toks[-1], " ".join(toks[:-1])
        elif len(toks) >= 2 and re.match(r"^\d+[A-Za-z]?$", toks[0]):
            num, street = toks[0], " ".join(toks[1:])
        else:
            num, street = "", fa_main
    m = re.match(r"^(\d+[A-Za-z]?(?:/\d+[A-Za-z]?)?)[\-/](?:LOC|LOCAL|AP|APT|APTO|DEPTO|INT)\b", num, re.I)
    if m:  # 1432-Loc 6：门牌后面接的是单元
        num = m.group(1)
    g = GeoAddress(number=num, route=street, lat=lat, lng=lng, formatted=fa, id=txt(it.get("adcode")))
    g.localities = [x for x in (txt(it.get("district")), txt(it.get("city")), txt(it.get("township"))) if x]
    level = txt(it.get("level"))
    g.location_type = AMAP_LEVEL.get(level, "APPROXIMATE" if level else ("ROOFTOP" if num else "APPROXIMATE"))
    return g if (g.route or g.number) else None


def _put(g: GeoAddress, types: list[str], name: str) -> None:
    if not name:
        return
    t = set(types)
    if "street_number" in t:
        g.number = name
    elif "route" in t:
        g.route = name
    elif "subpremise" in t:
        g.subpremise = name
    elif "premise" in t:
        g.premise = name
    elif "postal_code" in t:
        g.postal_code = name
    elif t & set(LOCALITY_TYPES):
        g.localities.append(name)


@dataclass
class GeoCheck:
    geo: GeoAddress
    fields: dict[str, str]      # number / route / postal_code / locality / subpremise -> 判定
    flags: list[str]            # 原因码
    verdict: str                # VERIFIED / PLAUSIBLE / MISSING_NUMBER / STREET_LEVEL / REJECTED
    hard: list[str] = field(default_factory=list)  # 否决的依据：number / route / postcode


def check(eng: Engine, p, g: GeoAddress, cov=None) -> GeoCheck:
    """把一条 geo 门址代回解析后的输入（p）和参考数据，逐字段判定。
    cov：试点范围判断。范围外的地址参考库里没有，片区 / 邮编位置改用全国地名 / 邮编表核对，不查同名道路。"""
    m, ref = eng.market, eng.ref
    outside = cov is not None and cov.status == "OUTSIDE"
    fields: dict[str, str] = {}
    flags: list[str] = []
    itxt = " " + " ".join(" ".join(key(t, m).split()) for t in p.tokens) + " "

    # ---- 门牌
    if not g.number or g.location_type in STREET_LEVEL_TYPES:
        fields["number"] = "MISSING"
    elif not p.number:
        fields["number"] = "INFERRED"
    else:
        mine = {number_key(v) for v in eng._number_variants(p.number)}
        theirs = {number_key(v) for v in eng._number_variants(g.number)}
        if mine & theirs or f" {number_key(g.number)} " in itxt:  # 解析选错了数字、但原文里有 geo 的门牌也算
            fields["number"] = "CONFIRMED"
        elif {x.rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for x in mine} & {x.rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                                                                     for x in theirs}:
            fields["number"] = "CORRECTED"  # 12A / 12：只差附加字母
        else:
            fields["number"] = "CONFLICT"
    # ---- 道路
    pc_re = eng.rules.pc_re
    if not g.route:
        fields["route"] = "MISSING"
    else:  # 参考库判定（别名、全称 / 简称）+ 原文道路段判定（不被城镇名冒充，见 geo_text.py）
        by_text = route_match(g.route, p.raw, pc_re)
        fields["route"] = by_text if outside else _combine(_route(eng, p, g, itxt), by_text)
        if outside and numbered_only(g.route):
            flags.append("GEO_AMBIGUOUS")  # 编号路名（Street 7）同城有很多条，范围外又没有参考库可查
    # ---- 邮编（所写邮编的中心离 geo 坐标太远：二者必有一错）
    g_pc = norm_postcode(g.postal_code, m) if g.postal_code else ""
    if not p.postcode:
        fields["postal_code"] = "INFERRED" if g_pc else ""
    elif not g_pc or g_pc == p.postcode or postcode_prefix(g_pc, m) == postcode_prefix(p.postcode, m) == p.postcode \
            or (m in ("GB", "IE") and postcode_prefix(g_pc, m) == postcode_prefix(p.postcode, m)):
        fields["postal_code"] = "CONFIRMED"  # 英国 / 爱尔兰一户一码：同一个邮区内只差最后几位，与本引擎同样不算替换
    else:
        fields["postal_code"] = "REPLACED"
    pc = None if outside else eng._postcode_point(p)
    if pc and haversine(pc[0], pc[1], g.lat, g.lng) > eng._pc_far():
        flags.append("GEO_POSTCODE_FAR")
    elif pc is None and p.postcode and (eng.m.cls == "A" or m in FINE_PC):  # 参考库没有这个邮编：用全国邮编表的位置
        #（东南亚、中东的全国邮编表坐标粗，不据此判断）
        hits = gazetteer(ref)._postcode_place(p.postcode) if gazetteer(ref).ok else None
        if hits and all(haversine(h[0], h[1], g.lat, g.lng) > max(NATIONAL_PC_FAR_M, eng._pc_far()) for h in hits):
            flags.append("GEO_POSTCODE_FAR")
    # ---- 片区：所写片区要包含 geo 坐标（名称一致也算）
    if outside:  # 所写城镇 / 邮编所在地（全国地名表）要包含 geo 坐标
        fields["locality"] = locality_check(cov, g.lat, g.lng) or ("INFERRED" if g.localities else "")
    elif p.areas:
        names = {" ".join(key(x, m).split()) for x in g.localities}
        inside = any(s.text in names for s in p.areas) or any(
            haversine(ref.areas[a].lat, ref.areas[a].lng, g.lat, g.lng) <= max(ref.areas[a].radius_m * 1.5, 2000)
            for s in p.areas for a in s.ids[:5])
        fields["locality"] = "CONFIRMED" if inside else "CONFLICT"
    else:
        fields["locality"] = "INFERRED" if g.localities else ""
    # ---- 单元
    if p.unit and g.subpremise:
        a, b = (re.sub(r"^(?:UNIT|APARTMENT|APT|SUITE|FLAT|SHOP|OFFICE|ROOM|LEVEL)\.?", "", number_key(x))
                for x in (p.unit, g.subpremise))
        fields["subpremise"] = "CONFIRMED" if a == b or a.endswith(b) or b.endswith(a) else "CONFLICT"
    elif g.subpremise:
        fields["subpremise"] = "INFERRED"
    # ---- 同名道路：别处也有这个门牌，输入里又没有邮编 / 片区能区分
    if fields["number"] in ("CONFIRMED", "CORRECTED") and g.route and fields["postal_code"] != "CONFIRMED" \
            and fields["locality"] != "CONFIRMED" and not outside and _elsewhere(eng, g):
        flags.append("GEO_AMBIGUOUS")

    # ---- 结论
    hard = [f for f in ("number", "route") if fields[f] == "CONFLICT"]
    if outside and fields["locality"] == "CONFLICT":
        hard.append("locality")  # 所写城镇里没有这处：geo 选了别的城镇的同名路
    if "GEO_POSTCODE_FAR" in flags and (eng.pc_weight >= 1.5 or outside):  # 商户邮编不准的市场（pc_weight 减半）不据此否决
        hard.append("postcode")
    if fields["number"] == "MISSING" or fields["route"] == "MISSING":
        verdict = "STREET_LEVEL"
        flags.append("GEO_STREET_LEVEL_ONLY")
    elif hard:
        verdict = "REJECTED"
        flags += [{"number": "GEO_NUMBER_CONFLICT", "route": "GEO_ROUTE_CONFLICT", "locality": "AREA_STREET_MISMATCH",
                   "postcode": "GEO_POSTCODE_FAR"}[h] for h in hard if h != "postcode"]
    elif fields["number"] == "INFERRED":
        verdict = "MISSING_NUMBER"
        flags.append("GEO_NUMBER_INFERRED")
    elif fields["number"] == "CONFIRMED" and fields["route"] == "CONFIRMED" and not (
            set(flags) & {"GEO_AMBIGUOUS", "GEO_POSTCODE_FAR"}) and fields["postal_code"] != "REPLACED" \
            and fields["locality"] != "CONFLICT" and fields.get("subpremise") != "CONFLICT":
        verdict = "VERIFIED"
    else:
        verdict = "PLAUSIBLE"
        flags += [c for f, c in (("route", "GEO_ROUTE_CORRECTED"), ("number", "GEO_NUMBER_CORRECTED"))
                  if fields[f] == "CORRECTED"]
        flags += ["GEO_ROUTE_INFERRED"] if fields["route"] == "INFERRED" else []
        flags += ["POSTCODE_REPLACED"] if fields["postal_code"] == "REPLACED" else []
        flags += ["AREA_STREET_MISMATCH"] if fields["locality"] == "CONFLICT" else []
    return GeoCheck(g, fields, list(dict.fromkeys(flags)), verdict, hard)


def _combine(by_ref: str, by_text: str) -> str:
    """参考库判定与原文判定合并：两边一致照用；参考库确认、原文对不上（城镇名冒充路名）-> 纠正；
    参考库冲突、原文对得上（别的语言 / 缩写的写法）-> 纠正；都只是"没写"时以原文为准。"""
    if by_ref == by_text:
        return by_ref
    if by_ref == "CONFIRMED":
        return "CORRECTED" if by_text == "CONFLICT" else "CONFIRMED"
    if by_ref == "CORRECTED":
        return "CONFIRMED" if by_text == "CONFIRMED" else "CORRECTED"
    if by_ref == "CONFLICT":
        return "CORRECTED" if by_text in ("CONFIRMED", "CORRECTED") else "CONFLICT"
    return by_text  # 参考库判 INFERRED（原文里没有可对照的路名）


def _route(eng: Engine, p, g: GeoAddress, itxt: str) -> str:
    m, ref = eng.market, eng.ref
    rk = " ".join(key(g.route, m).split())
    rck = core_key(g.route, m)
    if f" {rk} " in itxt:
        return "CONFIRMED"
    types = type_words(m)
    ids = set(ref.street_keys.get(rk, ())) | set(ref.street_core.get(rck, ()))
    mine = {t for t in itxt.split() if t in types}
    theirs = set(rk.split()) & types
    type_clash = bool(mine and theirs and not (mine & theirs))  # Station Parade ≠ Station Road
    if len(rck) >= 4 and f" {rck} " in itxt and not type_clash:
        return "CONFIRMED"  # 只是没写 / 写法不同的类型词（Bandeirantes = Avenida dos Bandeirantes）
    from .parse import SUFFIX_MARKETS
    plain = ("exact", "core", "alias") + (("suffix",) if m in SUFFIX_MARKETS else ())  # 只写姓在这些国家是常规写法
    for s in p.streets:
        if ids & set(s.ids):  # 参考库里的别名、全称 / 简称对上了同一条路
            return "CONFIRMED" if s.how in plain and not type_clash else "CORRECTED"
    score = fuzz.partial_ratio(rck or rk, itxt) if len(rck or rk) >= 5 else 0
    if score >= 88 and not type_clash:
        return "CORRECTED"  # 拼错 / 少写了几个词
    if type_clash and len(rck) >= 4 and f" {rck} " in itxt:
        return "CONFLICT"
    # 只写姓 / 全称的一部分（Żaryna = Stanisława Żaryna，Ziemskiego = Generała Karola Ziemskiego „Wachnowskiego”）：
    # 输入里认出的路名的词全在 geo 路名里（或反过来），而且最后一个实词一致
    geo_words = [w for w in rck.split() if w.isalpha()]
    for s in p.streets:
        words = [w for w in core_key(s.text, m).split() if w.isalpha() and w not in types]
        if words and geo_words and (set(words) <= set(geo_words) or set(geo_words) <= set(words)) and not type_clash:
            return "CONFIRMED" if m in SUFFIX_MARKETS and words[-1] in geo_words else "CORRECTED"
    other = [s for s in p.streets if s.how in ("exact", "core") and fuzz.ratio(s.text, rk) < 80]
    if other or score >= 60:
        return "CONFLICT"  # 输入写的是另一条路
    return "INFERRED"  # 输入里没有可以对照的路名（只写了楼名 / 片区）：路名是 geo 推断的


def _elsewhere(eng: Engine, g: GeoAddress) -> bool:
    """同名道路在 2 公里外也有这个门牌（参考库有门牌数据时按门牌查，没有时只看同名道路）。"""
    ref, m = eng.ref, eng.market
    rk, rck = " ".join(key(g.route, m).split()), core_key(g.route, m)
    ids = set(ref.street_keys.get(rk, ())) | (set(ref.street_core.get(rck, ())) if len(rck) >= 4 else set())
    far = [sid for sid in ids if dist_to_street(ref, sid, g.lat, g.lng) > ELSEWHERE_M][:40]
    if not far:
        return False
    if not ref.has_addresses and not getattr(ref, "osm_count", 0):
        return True
    return any(ref.addresses(far, v) for v in eng._number_variants(g.number))


# ---------------------------------------------------------------------------------------------- 结论
def validate_with_geo(eng: Engine, text: str, geo, strictness: str = "BALANCED",
                      min_confidence: float | None = None, use_engine: bool = True) -> Result:
    """geo 的结果核对后定结论；geo 解析错了或没有结果时用本引擎的结论（geo 结果作为候选）。
    use_engine=False：评测用，假装本引擎什么都没找到（参考库没有覆盖的地方），只看核对层自己能不能把住关。"""
    ours = eng.validate(text, strictness=strictness, min_confidence=min_confidence)
    if not use_engine:
        ours = Result(eng.market, FIX, "OTHER", None, None, ours.parsed, None, ["NO_MATCH"], {}, [], ours.parser)
    p = ours.parsed
    cov = ours.coverage if use_engine else None
    checks = [check(eng, p, g, cov) for g in parse_geo(geo)]
    if not checks:
        ours.reasons.append("GEO_NO_RESULT")
        return ours
    if cov is not None and cov.status == "OUTSIDE":
        return _outside_with_geo(eng, ours, checks, strictness)
    rank = {"VERIFIED": 4, "PLAUSIBLE": 3, "MISSING_NUMBER": 2, "STREET_LEVEL": 1, "REJECTED": 0}
    c = max(checks, key=lambda x: rank[x.verdict])
    g = c.geo
    near = ours.lat is not None and haversine(ours.lat, ours.lng, g.lat, g.lng) <= AGREE_M
    far = ours.lat is not None and haversine(ours.lat, ours.lng, g.lat, g.lng) > DISAGREE_M
    ours_premise = ours.action in (ACCEPT, ADD_SUB) and ours.granularity == "PREMISE"
    geo_cand = _cand(g)

    if c.verdict == "REJECTED" and c.hard == ["postcode"] and ours.granularity not in ("PREMISE", "PREMISE_PROXIMITY"):
        # 门牌、道路都对上，只是所写邮编离得远（商户邮编写错也常见），本引擎又没找到这个门牌 -> 给 geo 的位置，请用户确认
        res = _from_geo(eng, ours, c, CONFIRM, [])
        res.candidates = [geo_cand] + ([eng._describe(ours.best)] if ours.best and far else [])
        return res
    if c.verdict in ("REJECTED", "STREET_LEVEL") or (c.verdict == "MISSING_NUMBER" and ours.action != FIX):
        # geo 多半解析错了 / 只到道路级：以本引擎为准，geo 结果作为候选
        ours.reasons += c.flags + ["GEO_REJECTED"]
        ours.candidates = (ours.candidates or []) + [geo_cand]
        return ours
    if c.verdict == "VERIFIED":
        if far and ours_premise:  # 两边都和输入自洽、却相距很远：同名道路各选了一条
            res = _from_geo(eng, ours, c, CONFIRM, ["GEO_ENGINE_DISAGREE"])
            res.candidates = [geo_cand, eng._describe(ours.best)] if ours.best else [geo_cand]
            return res
        action = ACCEPT
        extra = ["GEO_VERIFIED"] + (["GEO_CONFIRMED_BY_ENGINE"] if near else [])
        if g.location_type == "RANGE_INTERPOLATED":
            action, extra = CONFIRM, extra + ["PREMISE_INTERPOLATED"]
        if strictness == "STRICT" and not near and c.fields["postal_code"] != "CONFIRMED":
            action = CONFIRM  # 严格模式：geo 门址还要有本引擎或所写邮编印证
        res = _from_geo(eng, ours, c, action, extra)
        if near and ours.confidence is not None:
            res.confidence, res.confidence_note = ours.confidence, ours.confidence_note
        if action == ACCEPT and min_confidence is not None and res.confidence is not None \
                and res.confidence < min_confidence:
            res.action = CONFIRM
            res.reasons.append("LOW_CONFIDENCE")
        return res
    if c.verdict == "PLAUSIBLE" and c.flags == ["POSTCODE_REPLACED"] and strictness != "STRICT" \
            and "PREMISE|POSTCODE_REPLACED" in eng.policy:
        # 只有邮编与官方不同，而这个市场开发集上"门牌对上 + 邮编被替换"几乎都对（巴西、立陶宛，与本引擎同一条放宽规则）
        return _from_geo(eng, ours, c, ACCEPT, ["GEO_VERIFIED"] + (["GEO_CONFIRMED_BY_ENGINE"] if near else []))
    if c.verdict == "PLAUSIBLE":
        if near and ours.action in (ACCEPT, ADD_SUB):  # 本引擎由官方地址点确认了同一处：geo 的改动可信
            ours.reasons += ["GEO_CONFIRMED_BY_ENGINE"]
            return ours
        res = _from_geo(eng, ours, c, CONFIRM, [])
        res.candidates = [geo_cand] + ([eng._describe(ours.best)] if ours.best and far else [])
        return res
    # MISSING_NUMBER 且本引擎也判 FIX：用户没写门牌，geo 补出来的门牌不能当真
    res = _from_geo(eng, ours, c, FIX, ["MISSING_PREMISE"])
    res.granularity = "ROUTE"
    return res


def _outside_with_geo(eng: Engine, ours: Result, checks: list[GeoCheck], strictness: str) -> Result:
    """试点范围外的地址：参考库没有它，只能核对 geo 门址与输入是否逐字段一致（门牌、道路、城镇 / 邮编位置）。
    全部一致 -> ACCEPT（GEO_VERIFIED，并标 OUTSIDE_COVERAGE：没有参考数据独立印证）；改动过的 -> CONFIRM；
    冲突 / 只到道路级 -> 保留范围外的结论（城镇级），geo 结果作为候选。"""
    rank = {"VERIFIED": 4, "PLAUSIBLE": 3, "MISSING_NUMBER": 2, "STREET_LEVEL": 1, "REJECTED": 0}
    c = max(checks, key=lambda x: rank[x.verdict])
    if c.verdict in ("REJECTED", "STREET_LEVEL"):
        ours.reasons += c.flags + ["GEO_REJECTED"]
        ours.candidates = (ours.candidates or []) + [_cand(c.geo)]
        return ours
    if c.verdict == "MISSING_NUMBER":
        res = _from_geo(eng, ours, c, FIX, ["OUTSIDE_COVERAGE", "MISSING_PREMISE"])
        res.granularity = "ROUTE"
        return res
    ok = c.verdict == "VERIFIED" and c.fields["locality"] == "CONFIRMED" and strictness != "STRICT" \
        and c.geo.location_type != "RANGE_INTERPOLATED"
    return _from_geo(eng, ours, c, ACCEPT if ok else CONFIRM, ["OUTSIDE_COVERAGE"] + (["GEO_VERIFIED"] if ok else []))


def _from_geo(eng: Engine, ours: Result, c: GeoCheck, action: str, extra: list[str]) -> Result:
    g, f = c.geo, c.fields
    m = eng.market
    level = {"CONFIRMED": "CONFIRMED", "CORRECTED": "UNCONFIRMED_BUT_PLAUSIBLE", "INFERRED": "CONFIRMED",
             "REPLACED": "CONFIRMED", "CONFLICT": "UNCONFIRMED_AND_SUSPICIOUS", "MISSING": "UNCONFIRMED_BUT_PLAUSIBLE"}
    comps: dict[str, dict] = {}
    if g.route:
        comps["route"] = {"text": g.route, "level": level[f["route"]], "spellCorrected": f["route"] == "CORRECTED",
                          "inferred": f["route"] == "INFERRED"}
    if g.number and f["number"] != "MISSING":
        comps["street_number"] = {"text": g.number, "level": "UNCONFIRMED_BUT_PLAUSIBLE" if f["number"] == "INFERRED"
                                  else level[f["number"]], "inferred": f["number"] == "INFERRED"}
    if g.postal_code:
        comps["postal_code"] = {"text": norm_postcode(g.postal_code, m), "level": level.get(f["postal_code"], "CONFIRMED"),
                                "inferred": f["postal_code"] == "INFERRED", "replaced": f["postal_code"] == "REPLACED"}
    if g.localities:
        comps["locality"] = {"text": g.localities[0], "level": level.get(f["locality"], "CONFIRMED"),
                             "inferred": f["locality"] == "INFERRED"}
    if ours.parsed.unit or g.subpremise:
        comps["subpremise"] = {"text": ours.parsed.unit or g.subpremise, "level": level.get(f.get("subpremise", ""),
                                                                                          "UNCONFIRMED_BUT_PLAUSIBLE")}
    gran = "ROUTE" if f["number"] in ("MISSING", "INFERRED") else (
        "PREMISE_PROXIMITY" if g.location_type == "RANGE_INTERPOLATED" else "PREMISE")
    best = Hypothesis(0.0, point={"id": g.id or -3, "number": g.number, "street": None, "unit": g.subpremise,
                                  "postcode": norm_postcode(g.postal_code, m) if g.postal_code else "",
                                  "locality": g.localities[0] if g.localities else "", "lat": g.lat, "lng": g.lng})
    reasons = [r for r in ours.reasons if r in ("NON_ADDRESS_INFO_EXTRACTED",)] + c.flags + extra
    res = Result(eng.market, action, gran, g.lat, g.lng, ours.parsed, best, list(dict.fromkeys(reasons)), comps,
                 [], f"{ours.parser}+geo")
    res.coverage = ours.coverage  # 试点范围判断随结论一起返回
    return res


def _cand(g: GeoAddress) -> dict:
    return {"street": g.route, "number": g.number, "postcode": g.postal_code,
            "area": g.localities[0] if g.localities else "", "lat": g.lat, "lng": g.lng, "source": "geo"}
