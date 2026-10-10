"""与 Google Address Validation（validateAddress）对齐的响应层：字段、取值和含义按 Google AV 的定义。

内部结论（ACCEPT / CONFIRM / FIX、粒度、各组件的确认级别）不变，评测数字照旧；这里负责：
  - 每个国家的地址"该有哪些字段"按 Google 的地址格式元数据（address_formats.json，scripts/fetch_address_formats.py
    从 Google 的 Address Data Service 下载）：必填字段 require（A 街道 C 城市 S 州 / 省 Z 邮编 D 区）
    -> missingComponentTypes；排版 fmt -> formattedAddress；州 / 省列表及其邮编前缀 -> 从邮编补全州 / 省；
  - 补全 Google 会补的组件（inferred）：城市、州 / 省、国家（Overture 行政区层级 + GeoNames 全国地名表）；
  - Google 的取值：CONFIRM_ADD_SUBPREMISES 只用于美国地址（其他国家返回 CONFIRM，subpremise 列入缺失）、
    日本街区级门牌的粒度是 BLOCK、组件类型用 Google 的类型名（premise、sublocality_level_1、
    administrative_area_level_1 ……）。
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from .coverage import norm, town_radius
from .reference import haversine
from .text import fold, script_of

FORMATS_PATH = Path(__file__).with_name("address_formats.json")
_FORMATS: dict | None = None

# 州 / 省（%S）在 Google 里是哪一级：意大利、西班牙的 %S 是省（Google 的 administrative_area_level_2）
ADMIN2 = {"IT", "ES"}
# 组件在响应里的顺序（从小到大，与 Google 一致）
ORDER = ["subpremise", "premise", "street_number", "route", "plus_code", "neighborhood", "sublocality_level_2",
         "sublocality_level_1", "locality", "postal_town", "administrative_area_level_2",
         "administrative_area_level_1", "postal_code", "country"]

# 国家名：本地语言 / 英文（Google 按输入语言返回）
COUNTRY = {
    "AU": ({}, "Australia"), "DE": ({"de": "Deutschland"}, "Germany"), "FR": ({"fr": "France"}, "France"),
    "NL": ({"nl": "Nederland"}, "Netherlands"), "AE": ({"ar": "الإمارات العربية المتحدة"}, "United Arab Emirates"),
    "SA": ({"ar": "المملكة العربية السعودية"}, "Saudi Arabia"), "MY": ({"ms": "Malaysia"}, "Malaysia"),
    "ID": ({"id": "Indonesia"}, "Indonesia"), "TH": ({"th": "ประเทศไทย"}, "Thailand"),
    "VN": ({"vi": "Việt Nam"}, "Vietnam"), "PH": ({}, "Philippines"), "CA": ({"fr": "Canada"}, "Canada"),
    "MX": ({"es": "México"}, "Mexico"), "PR": ({"es": "Puerto Rico"}, "Puerto Rico"), "BR": ({"pt": "Brasil"}, "Brazil"),
    "AR": ({"es": "Argentina"}, "Argentina"), "CL": ({"es": "Chile"}, "Chile"), "CO": ({"es": "Colombia"}, "Colombia"),
    "GB": ({}, "United Kingdom"), "IE": ({}, "Ireland"), "BE": ({"fr": "Belgique", "nl": "België"}, "Belgium"),
    "LU": ({"fr": "Luxembourg"}, "Luxembourg"), "CH": ({"de": "Schweiz", "fr": "Suisse", "it": "Svizzera"}, "Switzerland"),
    "AT": ({"de": "Österreich"}, "Austria"), "IT": ({"it": "Italia"}, "Italy"), "ES": ({"es": "España"}, "Spain"),
    "PT": ({"pt": "Portugal"}, "Portugal"), "DK": ({"da": "Danmark"}, "Denmark"), "SE": ({"sv": "Sverige"}, "Sweden"),
    "NO": ({"no": "Norge"}, "Norway"), "FI": ({"fi": "Suomi", "sv": "Finland"}, "Finland"),
    "EE": ({"et": "Eesti"}, "Estonia"), "LV": ({"lv": "Latvija"}, "Latvia"), "LT": ({"lt": "Lietuva"}, "Lithuania"),
    "PL": ({"pl": "Polska"}, "Poland"), "CZ": ({"cs": "Česko"}, "Czechia"), "SK": ({"sk": "Slovensko"}, "Slovakia"),
    "HU": ({"hu": "Magyarország"}, "Hungary"), "SI": ({"sl": "Slovenija"}, "Slovenia"),
    "HR": ({"hr": "Hrvatska"}, "Croatia"), "BG": ({"bg": "България"}, "Bulgaria"), "NZ": ({}, "New Zealand"),
    "JP": ({"ja": "日本"}, "Japan"), "IN": ({}, "India"), "KW": ({"ar": "الكويت"}, "Kuwait"),
    "BH": ({"ar": "البحرين"}, "Bahrain"), "OM": ({"ar": "عُمان"}, "Oman"), "QA": ({"ar": "قطر"}, "Qatar"),
    "EG": ({"ar": "مصر"}, "Egypt"), "KZ": ({"kk": "Қазақстан", "ru": "Казахстан"}, "Kazakhstan"),
    "UZ": ({"uz": "Oʻzbekiston"}, "Uzbekistan"), "PE": ({"es": "Perú"}, "Peru"),
    "DO": ({"es": "República Dominicana"}, "Dominican Republic"), "TR": ({"tr": "Türkiye"}, "Türkiye"),
    "ZA": ({}, "South Africa"), "SG": ({}, "Singapore"), "US": ({}, "United States"),
}
# 拉丁字母写的输入里，可以按道路类型词判断是哪种语言（比利时、瑞士、加拿大、芬兰是多语国家）
LANG_HINTS = {
    "BE": [("nl", r"(STRAAT|LAAN|PLEIN|STEENWEG|DREEF|KAAI|LEI)\b")],
    "CH": [("fr", r"\b(RUE|AVENUE|CHEMIN|ROUTE|PLACE|QUAI)\b"), ("it", r"\b(VIA|PIAZZA|VIALE|VICOLO)\b")],
    "CA": [("fr", r"\b(RUE|CHEMIN|BOULEVARD|BOUL|AVENUE DU|MONTEE)\b")],
    "FI": [("sv", r"(GATAN|VAGEN|GRAND|STIGEN)\b")],
    "LU": [("de", r"(STRASSE|STR|WEG)\b")],
}
LATIN_LANGS = {"en", "de", "fr", "nl", "ms", "id", "vi", "es", "pt", "it", "da", "sv", "no", "fi", "et", "lv", "lt",
               "pl", "cs", "sk", "hu", "sl", "hr", "tr", "uz", "tl"}
_CJK = re.compile(r"[぀-ヿ㐀-鿿豈-﫿]")
_CYR = re.compile(r"[Ѐ-ӿ]")


def formats() -> dict:
    global _FORMATS
    if _FORMATS is None:
        _FORMATS = json.loads(FORMATS_PATH.read_text(encoding="utf-8")) if FORMATS_PATH.exists() else \
            {"defaults": {"fmt": "%N%n%O%n%A%n%C", "require": "AC"}, "countries": {}}
    return _FORMATS


def country_format(cc: str) -> dict:
    d = formats()
    return {**d["defaults"], **d["countries"].get(cc, {})}


def admin_type(cc: str) -> str:
    return "administrative_area_level_2" if cc in ADMIN2 else "administrative_area_level_1"


def city_type(cc: str) -> str:
    return "postal_town" if cc == "GB" else "locality"  # 英国的城市是邮政城镇（Google 用 postal_town）


def uses(cc: str, letter: str) -> bool:
    return f"%{letter}" in (country_format(cc).get("fmt") or "")


def script(text: str) -> str:
    s = script_of(text)
    if s != "latin":
        return s
    if _CJK.search(text):
        return "cjk"
    if _CYR.search(text):
        return "cyrillic"
    return "latin"


def language_of(text: str, cc: str, languages: tuple[str, ...] = ()) -> str:
    """输入地址的语言（BCP-47 主标签）：按文字判断，拉丁字母按市场的拉丁语种（多语国家按道路类型词）。"""
    s = script(text)
    langs = list(languages) or [country_format(cc).get("lang") or "en"]
    if s == "arabic":
        return "ar"
    if s == "thai":
        return "th"
    if s == "cjk":
        return "ja" if cc == "JP" else "zh"
    if s == "cyrillic":
        return "bg" if cc == "BG" else "kk" if cc == "KZ" and "kk" in langs else "ru"
    t = fold(text)
    for lang, pat in LANG_HINTS.get(cc, []):
        if re.search(pat, t):
            return lang
    return next((x for x in langs if x in LATIN_LANGS), "en")


def country_name(cc: str, lang: str) -> str:
    local, en = COUNTRY.get(cc, ({}, cc))
    return local.get(lang) or en


def country_names(cc: str) -> set[str]:
    local, en = COUNTRY.get(cc, ({}, cc))
    out = {norm(en), norm(cc)} | {norm(v) for v in local.values()}
    name = country_format(cc).get("name")
    if name:
        out.add(norm(name))
    return {x for x in out if x}


# ---------------------------------------------------------------------------------------------- 州 / 省
ADMIN_WORDS = {"STATE", "OF", "REGION", "REGIAO", "PROVINCE", "PROVINCIA", "DE", "DEL", "DA", "DO", "ESTADO",
                  "WOJ", "WOJEWODZTWO", "COMUNIDAD", "PREFECTURE", "COUNTY", "CO", "DAERAH", "KHUSUS", "IBUKOTA",
                  "DKI", "THANH", "PHO", "TP", "TINH", "DISTRITO", "CAPITAL", "D", "C", "DC", "MAAKOND", "KRAJ",
                  "LAN", "AUTONOMA", "CIUDAD", "GOVERNORATE", "EMIRATE", "MANTIKA", "المنطقه", "منطقه", "اماره",
                  "محافظه", "จังหวัด", "THE", "TERRITORY", "WILAYAH", "PERSEKUTUAN", "KOTA", "KABUPATEN", "KAB",
                  "KECAMATAN", "KEC", "KELURAHAN", "KEL", "DESA", "ADM", "ADMINISTRASI"}


@dataclass
class Subdivisions:
    """一个国家的州 / 省（Google 地址元数据里的 sub_keys）：键（邮寄地址里的写法）、本地名、拉丁名、邮编前缀。"""
    cc: str
    keys: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    lnames: list[str] = field(default_factory=list)
    zips: list[re.Pattern | None] = field(default_factory=list)

    @classmethod
    def of(cls, cc: str) -> "Subdivisions":
        f = country_format(cc)
        keys = (f.get("sub_keys") or "").split("~") if f.get("sub_keys") else []

        def split(k: str) -> list[str]:
            return (f.get(k) or "").split("~") if f.get(k) else [""] * len(keys)
        names, lnames = split("sub_names"), split("sub_lnames")
        zips = [re.compile(f"(?:{z})") if z else None for z in split("sub_zips")]
        return cls(cc, keys, names + [""] * (len(keys) - len(names)), lnames + [""] * (len(keys) - len(lnames)),
                   zips + [None] * (len(keys) - len(zips)))

    def by_postcode(self, pc: str | None) -> int | None:
        """Google 元数据里各州 / 省的邮编前缀（澳洲 2xxx = NSW、巴西 0-1 = SP、加拿大 M = ON …）。"""
        if not pc or not self.keys:
            return None
        s = re.sub(r"[\s\-〒]", "", fold(pc))
        s = re.sub(r"^[A-Z]{1,2}-?(?=\d)", "", s) if self.cc not in ("CA", "GB", "IE", "NL", "AR", "MT") else s
        hits = [i for i, z in enumerate(self.zips) if z is not None and z.match(s)]
        return hits[0] if len(hits) == 1 else None

    def _tokens(self, i: int) -> list[set[str]]:
        out = []
        for n in (self.keys[i], self.names[i], self.lnames[i]):
            t = set(norm(n).split()) - ADMIN_WORDS
            if t:
                out.append(t)
        return out

    def by_names(self, names: list[str]) -> int | None:
        """按行政区名称（Overture 层级里的州 / 省名）找对应的州 / 省：先比整名，再比去掉通用词后的词。"""
        if not self.keys:
            return None
        cands = [norm(n) for n in names if n]
        for i in range(len(self.keys)):
            if {norm(self.keys[i]), norm(self.names[i]), norm(self.lnames[i])} & set(cands):
                return i
        best, size = None, 0
        for c in cands:
            ct = set(c.split()) - ADMIN_WORDS
            if not ct:
                continue
            for i in range(len(self.keys)):
                for t in self._tokens(i):
                    ok = t <= ct or (len(t) == 1 and len(ct) == 1 and len(next(iter(ct))) >= 5
                                     and next(iter(t)).startswith(next(iter(ct))))  # Harju maakond = Harjumaa
                    if ok and len(t) > size:
                        best, size = i, len(t)
        return best

    def in_text(self, text: str) -> int | None:
        """原文里写的州 / 省：完整名称（New South Wales、Selangor、東京都）任何位置都算；
        缩写（NSW、ON、SP、MI）只认第一段之后、原文大写的独立词。"""
        if not self.keys:
            return None
        segs = re.split(r"\s*[,;|\n،]\s*", text)
        tail = " ".join(segs[1:]) if len(segs) > 1 else ""
        full = f" {norm(text)} "
        for i in range(len(self.keys)):
            for n in (self.names[i], self.lnames[i], self.keys[i]):
                k = norm(n)
                if not k:
                    continue
                if _CJK.search(n) and len(n) >= 2 and n in text:
                    return i
                if len(k) >= 4 and f" {k} " in full and (n != self.keys[i] or len(k) >= 6):
                    return i
        for i, k in enumerate(self.keys):
            if 2 <= len(k) <= 4 and k.isupper() and k.isascii() and re.search(rf"(?<![\w.]){re.escape(k)}(?![\w.])", tail):
                return i
        return None

    def text(self, i: int, latin: bool) -> str:
        """邮寄地址里的写法：多数国家用元数据的键（NSW、ON、SP、CDMX、MI、東京都）；西班牙的键是车牌代码、
        阿联酋的键带"إمارة"，用名称；拉丁字母输入、键是当地文字时用拉丁名。"""
        if latin and self.lnames[i] and script(self.keys[i]) != "latin":
            return self.lnames[i]
        if self.cc in ("ES", "AE") and self.names[i]:
            return self.names[i]
        return self.keys[i]


_SUBS: dict[str, Subdivisions] = {}


def subdivisions(cc: str) -> Subdivisions:
    if cc not in _SUBS:
        _SUBS[cc] = Subdivisions.of(cc)
    return _SUBS[cc]


# ---------------------------------------------------------------------------------------------- 行政区层级
@dataclass
class Node:
    name: str
    subtype: str
    local_type: str = ""
    names: dict = field(default_factory=dict)  # 语种 -> 名称

    def label(self, lang: str) -> str:
        n = self.names.get(lang)
        if not n and lang != "en" and script(self.name) != "latin" and lang in LATIN_LANGS:
            n = self.names.get("en")
        n = n or self.name
        if " - " in n and not self.names.get(lang):  # 比利时双语名 Schaerbeek - Schaarbeek：取第一种
            n = n.split(" - ")[0]
        return n


class Divisions:
    """一个市场的 Overture 行政区（data/markets/<市场>/division_areas.parquet 的边界 + divisions.parquet 的层级）：
    点 -> 从国家到最小行政区的层级链（国家 > 州 > 县 > 城市 > 区 > 街区）。"""

    def __init__(self, ref):
        self.ok = False
        self.tree = None
        try:
            import pyarrow.parquet as pq
            import shapely
            from shapely import wkb
        except ImportError:
            return
        da_path, dv_path = ref.dir / "division_areas.parquet", ref.dir / "divisions.parquet"
        if not da_path.exists() or not dv_path.exists():
            return
        try:
            areas = pq.read_table(da_path, columns=["division_id", "subtype", "geometry"]).to_pylist()
            divs = pq.read_table(dv_path, columns=["id", "names", "subtype", "local_type", "hierarchies"]).to_pylist()
        except Exception:  # noqa: BLE001  数据损坏 / 旧格式：不补全
            return
        self.divs = {d["id"]: d for d in divs}
        self.area_div = []
        geoms = []
        for a in areas:
            if not a.get("geometry") or a["division_id"] not in self.divs:
                continue
            try:
                geoms.append(wkb.loads(a["geometry"]))
            except Exception:  # noqa: BLE001
                continue
            self.area_div.append(a["division_id"])
        if not geoms:
            return
        self.geoms = geoms
        self.shapely = shapely
        self.tree = shapely.STRtree(geoms)
        self.ok = True

    def _node(self, h: dict) -> Node:
        d = self.divs.get(h.get("division_id")) or {}
        nm = d.get("names") or {}
        names = dict(nm.get("common") or [])
        lt = d.get("local_type") or []
        lt = dict(lt).get("en", "") if lt else ""
        return Node(h.get("name") or nm.get("primary") or "", h.get("subtype") or d.get("subtype") or "", lt or "",
                    names)

    def chain(self, lat: float, lng: float) -> list[Node]:
        if not self.ok:
            return []
        idx = self.tree.query(self.shapely.Point(lng, lat), predicate="within")
        if len(idx) == 0:
            return []
        i = min(idx, key=lambda k: self.geoms[k].area)
        d = self.divs[self.area_div[i]]
        hs = d.get("hierarchies") or []
        if not hs:
            return [self._node({"division_id": d["id"], "name": (d.get("names") or {}).get("primary"),
                                "subtype": d.get("subtype")})]
        return [self._node(h) for h in hs[0]]


def divisions(ref) -> Divisions:
    d = ref.__dict__.get("_divisions")
    if d is None:
        d = ref.__dict__["_divisions"] = Divisions(ref)
    return d


# 城市（Google 的 locality）在 Overture 层级里是哪一级：多数市场按下面 city_node 的通用规则；
# 这几个市场按固定的级别找（加拿大 Markham / Toronto 而不是 North York、York Region；印尼取 Kota；泰国取 Khet；
# 越南取直辖市；葡萄牙取 concelho；智利取 comuna，不取 Gran Santiago）
CITY_LEVEL = {"CA": [("locality", "city"), ("county", "county")], "ID": [("county", "")], "TH": [("county", "")],
              "VN": [("region", "")], "PT": [("county", "")]}
CITY_DEEPEST = {"CL"}
CITY_GAZ_ONLY = {"GB", "IN", "SA"}  # 层级里没有城市这一级：按全国地名表
CITY_STRICT = {"IE", "SK", "CO"}  # 只认标成 city 的一级，其余按全国地名表（Fingal、Bratislava-Ružinov 不是邮寄城市）
CITYISH = {"state", "municipality", "emirate", "commune", "city"}
NOT_CITY = {"borough", "district", "suburb", "neighbourhood", "neighborhood", "quarter"}
_AFFIX = re.compile(r"^(?:Majlis (?:Bandaraya|Perbandaran|Daerah)(?: Diraja)? |Dewan Bandaraya |Partido de |"
                    r"Municipio de |Comune di |Città di |Ville de |Stadt |Gemeente |Emirate of |إمارة )|"
                    r"(?: [Kk]ommune?r?| stad| ciudad| Emirate)$")


def city_node(chain: list[Node], cc: str) -> Node | None:
    nodes = [n for n in chain if n.subtype not in ("country", "dependency")]
    if not nodes or cc in CITY_GAZ_ONLY:
        return None
    if cc in CITY_LEVEL:
        for sub, lt in CITY_LEVEL[cc]:
            hit = next((n for n in nodes if n.subtype == sub and (not lt or n.local_type == lt)), None)
            if hit is not None:
                return hit
        return None
    if cc in CITY_DEEPEST:
        locs = [n for n in nodes if n.subtype == "locality" and n.local_type not in NOT_CITY]
        return locs[-1] if locs else None
    for n in nodes:  # 1. 标成 city 的 locality（Paris、Madrid、Warszawa、文京区）
        if n.subtype == "locality" and n.local_type == "city":
            return n
    if cc in CITY_STRICT:
        return None
    has_loc = any(n.subtype in ("locality", "localadmin") for n in nodes)
    for n in nodes:  # 2. 本身就是城市的州 / 市镇（Berlin、Wien、Amstelveen、Københavns Kommune、Zürich、San Juan）
        if n.subtype in ("region", "county", "localadmin") and (
                n.local_type in CITYISH or (n.subtype == "region" and n.local_type == "region" and not has_loc)):
            return n
    for kind in ("locality", "localadmin"):  # 3. 最上面一级 locality（Teltow、Peñalolén、Vantaa、MP Kajang）
        for n in nodes:
            if n.subtype == kind and n.local_type not in NOT_CITY:
                return n
    return None


def clean_city(name: str, cc: str, known: set[str] | None = None) -> str:
    out = _AFFIX.sub("", name).strip()
    if cc in ("DK", "SE", "NO") and out != name and out.endswith("s") and known and norm(out[:-1]) in known:
        out = out[:-1]  # Københavns Kommune -> København；Sundbybergs kommun -> Sundbyberg
    return out or name


def gazetteer_city(gaz, lat: float, lng: float, lang: str, text: str = "", min_pop: int = 50000):
    """全国地名表里包含这个点的最大城市（人口 5 万以上，按人口估的城区半径）：(名称, 名称列表)。"""
    if gaz is None or not getattr(gaz, "cities", None):
        return None
    best = None
    for la, ln, pop, nms in gaz.cities:  # 百万人口以上的都市区比估的城区半径大（利雅得、伦敦的外围）
        r = town_radius(pop) * (1.5 if pop >= 1000000 else 1.0)
        if pop >= min_pop and (best is None or pop > best[2]) and haversine(lat, lng, la, ln) <= r:
            best = (la, ln, pop, nms)
    if best is None:
        return None
    return pick_name(best[3], lang, text), best[3]


def pick_name(nms: list[str], lang: str, text: str = "") -> str:
    """GeoNames 的多语种名称里挑一个：原文里写了的优先，其次与输入同一种文字的，最后取主名称。"""
    t = f" {norm(text)} "
    for n in nms:
        k = norm(n)
        if len(k) >= 3 and f" {k} " in t:
            return n
    want = {"ar": "arabic", "th": "thai", "ja": "cjk", "zh": "cjk", "bg": "cyrillic", "ru": "cyrillic",
            "kk": "cyrillic"}.get(lang, "latin")
    for n in nms:
        if script(n) == want:
            return n
    return nms[0]


def place_relation(a: str, b: str) -> str:
    """两个地名的关系："same"（同一处：Bogotá Distrito Capital = Bogotá、MILANO = Milano）、
    "part"（一个是另一个加区号 / 区名：Paris 15e Arrondissement、Praha 5）、""（不相干）。"""
    ka, kb = norm(a), norm(b)
    if not ka or not kb:
        return ""
    ca = " ".join(w for w in ka.split() if w not in ADMIN_WORDS) or ka
    cb = " ".join(w for w in kb.split() if w not in ADMIN_WORDS) or kb
    if ka == kb or ca == cb:
        return "same"
    return "part" if ka.startswith(kb + " ") or kb.startswith(ka + " ") else ""


def one_language(name: str, lang: str) -> str:
    """比利时、瑞士的双语名（Rue Simonis - Simonisstraat、Schaerbeek - Schaarbeek）按输入语言取一种。"""
    if " - " not in name:
        return name
    parts = [x.strip() for x in name.split(" - ") if x.strip()]
    if len(parts) != 2:
        return name
    if lang == "nl":
        nl = [x for x in parts if re.search(LANG_HINTS["BE"][0][1], fold(x))]
        return nl[0] if nl else parts[1]
    return parts[0]


def title(s: str) -> str:
    """官方地址表里全大写的地名（MELBOURNE、LISBOA）按 Google 的写法首字母大写。"""
    if s and s.isupper() and script(s) == "latin" and len(s) > 3:
        return re.sub(r"[^\W\d_]+", lambda m: m.group(0).capitalize(), s.lower())  # SAINT-DENIS -> Saint-Denis
    return s


# ---------------------------------------------------------------------------------------------- 排版
_LITERAL_PREFIX = re.compile(r"(?:CH|FI|HR|LT|SE|SI|L)-(?=%Z)|SINGAPORE (?=%Z)")


def format_lines(cc: str, parts: dict[str, str], lang: str = "") -> list[str]:
    """按 Google 地址元数据的 fmt 排版：%A 街道行 %C 城市 %S 州 / 省 %Z 邮编 %D 区（%N 姓名 %O 公司 %X 分拣码不用）。
    国家前缀（CH-8001、SE-111 51）不进 formattedAddress。"""
    f = country_format(cc)
    fmt = f.get("fmt") or "%N%n%O%n%A%n%C"
    if f.get("lfmt") and lang and script(" ".join(parts.values())) == "latin" and script(f.get("fmt", "")) != "latin":
        fmt = f["lfmt"]
    fmt = _LITERAL_PREFIX.sub("", fmt)
    if parts.get("S") and parts.get("C") and norm(parts["S"]) == norm(parts["C"]):
        parts = {**parts, "S": ""}  # 州 / 省与城市同名（Madrid、Kuala Lumpur、Hồ Chí Minh）只写一次
    lines = []
    for raw in fmt.split("%n"):
        line = re.sub(r"%([A-Z])", lambda m: f"\x00{parts.get(m.group(1), '')}\x00", raw)
        segs = line.split("\x00")
        # 去掉空字段旁边多出来的分隔符（"%C, %S" 只有城市时不留逗号）
        out = ""
        for k, s in enumerate(segs):
            if k % 2 == 0:
                out += s
            else:
                out += s if s else "\x01"
        out = re.sub(r"\x01\s*[,\-/]?\s*|\s*[,\-/]?\s*\x01", " ", out)
        out = re.sub(r"\s+,", ",", re.sub(r"\s+", " ", out)).strip(" ,-/")
        if out and out != "〒":
            lines.append(out)
    return lines


def join_lines(cc: str, lines: list[str], country: str, lang: str) -> str:
    """formattedAddress：各行用逗号连成一行，末尾接国家；日文按 Google 的写法从大到小连写（日本、〒170-0013 東京都豊島区…）。"""
    if not lines:
        return ""
    if cc == "JP" and lang == "ja":
        head = lines[0] + " " if lines[0].startswith("〒") else ""
        body = "".join(lines[1:] if head else lines)
        return f"{country}、{head}{body}" if country else f"{head}{body}"
    return ", ".join(lines + ([country] if country else []))


def required_missing(cc: str, present: set[str], building_only: bool = False) -> list[str]:
    """Google 的 missingComponentTypes：这个国家必填（require）却既不在输入里、也补不出来的组件类型。
    只有楼名的地址（商场、写字楼）不要求道路和门牌。"""
    req = country_format(cc).get("require") or "AC"
    miss = []
    if "A" in req and not building_only:
        if "route" not in present:
            miss.append("route")
        if "street_number" not in present:
            miss.append("street_number")
    if "C" in req and not ({"locality", "postal_town"} & present):
        miss.append(city_type(cc))
    if "S" in req and admin_type(cc) not in present and subdivisions(cc).keys:
        miss.append(admin_type(cc))
    if "Z" in req and "postal_code" not in present:
        miss.append("postal_code")
    if "D" in req and not ({"sublocality_level_1", "neighborhood"} & present):
        miss.append("sublocality_level_1")
    return miss


def next_action(action: str, cc: str) -> str:
    """CONFIRM_ADD_SUBPREMISES 只用于美国地址（Google 文档）：其他国家返回 CONFIRM，subpremise 列入缺失。"""
    return "CONFIRM" if action == "CONFIRM_ADD_SUBPREMISES" and cc != "US" else action


def verdict_flags(comps: list[dict], unresolved: list[str], missing: list[str]) -> dict:
    unconfirmed = list(dict.fromkeys(c["componentType"] for c in comps if c["confirmationLevel"] != "CONFIRMED"))
    unexpected = any(c.get("unexpected") for c in comps)
    return {
        "addressComplete": not unresolved and not missing and not unexpected,
        "hasUnconfirmedComponents": bool(unconfirmed) or bool(unresolved),
        "hasInferredComponents": any(c.get("inferred") for c in comps),
        "hasReplacedComponents": any(c.get("replaced") for c in comps),
        "hasSpellCorrectedComponents": any(c.get("spellCorrected") for c in comps),
        "_unconfirmed": unconfirmed,
    }


def component(ctype: str, text: str, level: str, lang: str, **flags) -> dict:
    c = {"componentName": {"text": text, "languageCode": lang}, "componentType": ctype, "confirmationLevel": level}
    c.update({k: True for k, v in flags.items() if v})
    return c


def sort_components(comps: list[dict]) -> list[dict]:
    rank = {t: i for i, t in enumerate(ORDER)}
    return sorted(comps, key=lambda c: rank.get(c["componentType"], len(ORDER)))


def postal_address(cc: str, lang: str, comps: list[dict], lines: list[str]) -> dict:
    by = {c["componentType"]: c["componentName"]["text"] for c in comps}
    out = {"regionCode": cc, "languageCode": lang, "addressLines": lines}
    for k, t in (("postalCode", "postal_code"), ("administrativeArea", admin_type(cc)),
                 ("locality", city_type(cc)), ("sublocality", "sublocality_level_1")):
        v = by.get(t) or (by.get("locality") if k == "locality" else by.get("neighborhood") if k == "sublocality"
                          else None)
        if v:
            out[k] = v
    return out


def bounds(lat: float, lng: float, half_m: float) -> dict:
    dlat = half_m / 111320.0
    dlng = dlat / max(0.2, abs(math.cos(math.radians(lat))))
    return {"low": {"latitude": lat - dlat, "longitude": lng - dlng},
            "high": {"latitude": lat + dlat, "longitude": lng + dlng}}
