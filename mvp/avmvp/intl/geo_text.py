"""geo 门址的路名与用户原文对照（不依赖参考库，各语言通用），geo_check 和 geo_free 共用。

真实 geo 返回的路名和用户写法常差在：别的语言的类型词（Carrer del Torrent de Can Miano = Torrent de Can Miano）、
缩写（Str. d. Nationen = Straße der Nationen）、只写姓（Baildona = Johna Baildona）、拼写（luis peixo = Lluís Peixó）。
反过来，geo 常把城镇 / 区名当成路名（12 auchingramont rd, Hamilton -> 12 HAMILTON ROAD；
улица Даулеткерея 37, Акжар -> Акжар улица 37）。所以：
  - 只和原文的"道路段"比：带门牌号的那一段（没有就取第一段），并去掉只在城镇 / 区段里出现的词；
  - 两边都去掉各语言的类型词、冠词 / 介词，逐词比（拼写容错、阿拉伯文与拉丁转写按辅音骨架）；
  - 编号道路的号码必须一致（Calle 16 ≠ Calle 46D）。
"""

from __future__ import annotations

import re
from functools import lru_cache

from rapidfuzz import fuzz

from .coverage import norm
from .text import TYPE_WORDS, fold, script_of, skeleton

TYPES = set().union(*TYPE_WORDS.values()) | {
    "ST", "RD", "AVE", "AV", "BLVD", "DR", "LN", "STREET", "ROAD", "AVENUE", "CALLE", "CL", "CLL", "C", "CARRER", "CR",
    "CARRERA", "CRA", "KR", "AVINGUDA", "AVDA", "PASSEIG", "PG", "PLACA", "PL", "TRAVESSERA", "RONDA", "CAMI",
    "AVENIDA", "JIRON", "JR", "PASAJE", "PSJE", "PJE", "CALLEJON", "CARRETERA", "AUTOPISTA", "PRIVADA", "PRIV",
    "CERRADA", "ANDADOR", "RUA", "R", "ALAMEDA", "TRAVESSA", "ESTRADA", "VIA", "VIALE", "PIAZZA", "PZA", "CORSO",
    "UL", "ULICA", "ALEJA", "AL", "OS", "OSIEDLE", "PLAC", "ULITSA", "ULITCA", "PROSPEKT", "PR", "PROSP", "PEREULOK",
    "PER", "MIKRORAION", "MKR", "MIKRORAYON", "KOSHESI", "DANGYLY", "SOKAK", "SOKAGI", "SK", "CADDESI", "CAD", "CD",
    "BULVARI", "BLV", "MAHALLESI", "MAH", "KUCHASI", "KOCHASI", "KO", "TOR", "BLOCK", "BLK", "WAY", "LANE", "DRIVE",
    "STR", "STRASSE", "STRAAT", "STRAATJE", "LAAN", "WEG", "PLEIN", "GASSE", "PLATZ", "ROUTE", "RTE", "ALL", "ALLEE",
    "CHEMIN", "CH", "IMPASSE", "IMP", "BD", "BOULEVARD", "RUE", "AVENUE", "JALAN", "JL", "JLN", "LORONG", "SOI",
    "THANON", "ถนน", "ซอย", "ถ", "ซ", "DUONG", "PHO", "شارع", "طريق", "ش", "سكة", "جادة", "جاده", "ممر", "زقاق",
    "NO", "NUMBER", "NR", "N", "NUM"}
# 楼栋 / 单元 / 门牌标记：不是路名（Building 4, Al Ilam St；Vila No-803, Road No-3315；منزل 20 شارع 18）
UNIT_WORDS = {"BUILDING", "BLDG", "BLD", "VILLA", "VILA", "HOUSE", "HSE", "FLAT", "APT", "APTO", "APARTMENT",
              "APARTAMENTO", "UNIT", "SHOP", "OFFICE", "CASA", "PISO", "DEPTO", "DPTO", "LOCAL", "BLOCO", "TORRE",
              "INTERIOR", "INT", "LOTE", "MANZANA", "MZ", "LT", "PORTAL", "PUERTA", "BAJO", "FLOOR", "LEVEL", "ROOM",
              "SUITE", "STE", "KV", "KVARTIRA", "DOM", "D", "OFIS", "DAIRE", "KAT", "NO", "منزل", "مبنى", "مبني", "فيلا",
              "شقة", "عمارة", "بناية", "دور", "طابق", "محل"}
PARTICLES = {"DE", "DEL", "DELA", "DA", "DAS", "DO", "DOS", "DI", "DU", "DES", "LA", "LE", "LES", "LOS", "LAS", "EL",
             "L", "D", "Y", "E", "ET", "VON", "VAN", "DER", "DEN", "THE", "OF", "AL", "ال"}
NUMBER_WORDS = {"NR", "NO", "N", "NUM", "NUMERO", "NRO", "NUMBER", "HAUSNUMMER", "HNR"}  # 门牌号前的标记
_UNIT_EXTRA = {"AP", "APPT", "APPARTEMENT", "APART", "APAR", "WOHNUNG", "WHG", "TOP", "STIEGE", "ETAGE", "PISO",
               "PLANTA", "ANDAR", "SALA", "LOJA", "CASA", "STALL", "LOT", "BLK", "BLOCK", "TORRE", "TOWER"}
_SEG = re.compile(r"\s*(?:[,;|\n،]|\s[-–—]\s)\s*")
_HOUSE = re.compile(r"(?<![\dA-Z])\d{1,4}[A-Z]?(?:[/\-]\d{1,4}[A-Z]?)?(?![\dA-Z\-])")  # 5 位以上多是邮编


# 路名里常见的缩写（方位、圣人、军衔 / 称谓），两边统一成全称再比
ABBR = {"NTE": "NORTE", "OTE": "ORIENTE", "PTE": "PONIENTE", "STA": "SANTA", "STO": "SANTO", "SRA": "SENHORA",
        "SR": "SENHOR", "GRAL": "GENERAL", "GEN": "GENERAL", "CEL": "CORONEL", "CNEL": "CORONEL", "TTE": "TENIENTE",
        "PDTE": "PRESIDENTE", "PRES": "PRESIDENTE", "STR": "STR", "NSRA": "SENHORA", "PROF": "PROFESSOR",
        "ENG": "ENGENHEIRO", "ING": "INGENIERO", "LIC": "LICENCIADO", "MCAL": "MARISCAL", "ALM": "ALMIRANTE"}


def _canon(w: str) -> str:
    """缩写展开；德 / 荷式粘连类型词统一：MARTINUSSTRASSE / MARTINUSSTR / MERESTRAAT -> …STR；
    变音的转写统一（Schoenbuehl = Schönbühl，ae / oe / ue 与 ä / ö / ü 去掉变音后相同；荷兰文 ij = y）。"""
    w = ABBR.get(w, w)
    if len(w) >= 4:
        w = w.replace("AE", "A").replace("OE", "O").replace("UE", "U").replace("IJ", "Y")
    return re.sub(r"(STRASSE|STRAAT|STRAßE|STR)$", "STR", w) if len(w) > 6 else w


def _core(words: list[str]) -> tuple[list[str], list[str]]:
    """(字母词, 带数字的词)：去掉类型词、冠词 / 介词和单个字母。"""
    alpha = [_canon(w) for w in words if not re.search(r"\d", w) and w not in TYPES and w not in PARTICLES
             and w not in UNIT_WORDS and len(w) >= 2]
    nums = [w for w in words if re.search(r"\d", w)]
    return alpha, nums


def street_part(text: str, pc_re: re.Pattern | None = None) -> tuple[list[str], list[str], set[str]]:
    """原文的道路段：(整段的词, 路名的词, 只出现在其他段——城镇 / 区——里的词)。
    道路段 = 第一个带门牌号的段（门牌号单独成段时并上前一段，没有前一段就并下一段）；没有门牌号就取第一段。
    路名的词按门牌号的位置取：门牌在段首取后面的词（27 Calle Virgen de la Salud），否则取最后一个门牌号前面的词
    （Rua Limeira 179 fundo casa：后面的 fundo casa、bloco 2、local 6 是单元 / 描述）。"""
    segs, plain, street, i = _street_segments(text, pc_re)
    if not segs:
        return [], [], set()
    words = [w for k in sorted(street) for w in norm(plain[k]).split()]
    toks = norm(plain[i]).split()
    nums = [k for k, w in enumerate(toks) if re.fullmatch(r"\d{1,4}[A-Z]?", w)]
    if not nums or len(street) > 1:
        name = words
    elif nums[0] == 0 or all(t in NUMBER_WORDS for t in toks[:nums[0]]) or all(
            t in UNIT_WORDS or t in _UNIT_EXTRA or re.fullmatch(r"U\d+[A-Z]?", t) for t in toks[:nums[0]]):
        name = toks[nums[0] + 1:]  # 门牌在段首（Nr. 9 Vogelberger Weg）；前面只有单元号（U56/1 Limestone Rd、Apt 7 43 Kent St）
    else:
        name = toks[:nums[-1]]
    other = {w for k, s in enumerate(segs) if k not in street for w in norm(s).split()}
    return words, name, other - set(words)


def _street_segments(text: str, pc_re: re.Pattern | None = None) -> tuple[list[str], list[str], list[int], int]:
    """(各段, 去掉邮编的各段, 道路段的下标, 带门牌号的那一段的下标)。"""
    segs = [s for s in _SEG.split(fold(text)) if s.strip()]
    if not segs:
        return [], [], [], 0
    plain = [pc_re.sub(" ", s) if pc_re else s for s in segs]  # 去掉邮编再找门牌
    with_no = [k for k, s in enumerate(plain) if _HOUSE.search(s)]

    def unit_only(k: int) -> bool:  # 只有单元词 + 号码的段（ap 202、Apt 169、Appartement 5）是单元，不是道路段
        alpha = [w for w in norm(plain[k]).split() if not re.search(r"\d", w) and len(w) > 1]
        return bool(alpha) and all(w in UNIT_WORDS or w in _UNIT_EXTRA for w in alpha)
    i = ([k for k in with_no if not unit_only(k)] or with_no or [0])[0]  # 第一个带门牌号的段
    street = [i]
    if not _core(norm(plain[i]).split())[0] and len(segs) > 1:
        street.append(i - 1 if i > 0 else i + 1)  # 门牌号单独成段：路名在前一段（C/ Joaquín Peralta, 12）或后一段
    return segs, plain, street, i


def other_words(text: str, pc_re: re.Pattern | None = None) -> set[str]:
    """道路段以外各段的全部词（与路名重复的也算：Thirlmere Way, Thirlmere 里第二段的 Thirlmere 是所写的城镇）。"""
    segs, _, street, _ = _street_segments(text, pc_re)
    return {w for k, s in enumerate(segs) if k not in street for w in norm(s).split()}


def _hit(w: str, pool: list[str], skel: set[str], blob: str) -> str:
    """一个词在另一边的对应："exact" / "fuzzy" / ""。"""
    if w in pool:
        return "exact"
    if len(w) >= 4 and f" {w}" in blob:  # 泰文等不分词的文字；粘连写法（拉丁文只认后面直接跟类型词的：PARK 不是 PARKSIDE）
        if not w.isascii() or any(t.startswith(w) and (t == w or t[len(w):] in TYPES) for t in blob.split()):
            return "exact"
    for x in pool:
        if len(w) >= 4 and len(x) >= 4 and abs(len(x) - len(w)) <= 4 and fuzz.ratio(w, x) >= 80:
            return "fuzzy"
        if len(x) >= 3 and len(w) > len(x) and w.startswith(x) and len(x) >= len(w) * 0.5:
            return "fuzzy"  # 缩写：KOSS -> KOSSAK、CONST -> CONSTANTINO
        if len(w) >= 3 and len(x) > len(w) and x.startswith(w) and len(w) >= len(x) * 0.5:
            return "fuzzy"
    sk = skeleton(w)
    return "fuzzy" if len(sk) >= 3 and sk in skel else ""


# 编号道路的类型词（阿拉伯文 / 英文 / 西文）：按"类型 + 号码"成对比较（شارع 3 جادة 6 ≠ شارع 6 جادة 3）
_NUM_TYPES = {"شارع": "ST", "ش": "ST", "STREET": "ST", "ST": "ST", "STR": "ST", "طريق": "RD", "ROAD": "RD",
              "RD": "RD", "جاده": "LN", "ج": "LN", "AVENUE": "AV", "AVE": "AV", "AV": "AV", "CALLE": "CL", "CL": "CL",
              "CLL": "CL"}
_NUM_SKIP = {"NO", "رقم", "NUMBER", "NR"}


def _num_pairs(words: list[str]) -> list[tuple[str, str]]:
    out = []
    for i, w in enumerate(words):
        t = _NUM_TYPES.get(w)
        if not t:
            continue
        j = i + 1
        while j < len(words) and words[j] in _NUM_SKIP:
            j += 1
        if j < len(words) and re.fullmatch(r"\d+[A-Z]?", words[j]):
            out.append((t, words[j]))
    return out


@lru_cache(maxsize=8192)
def _text_side(text: str, pc_re: re.Pattern | None) -> tuple:
    """原文这一侧（同一条原文要和全国库的几百个候选路名比，只算一次）。"""
    words, name, locality = street_part(text, pc_re)
    i_alpha = _core(name)[0]
    if locality and [w for w in i_alpha if w not in locality]:
        i_alpha = [w for w in i_alpha if w not in locality]  # 道路段里夹着的城镇名不算路名（只剩城镇名时保留）
    flat_words = norm(pc_re.sub(" ", fold(text)) if pc_re else text).split()
    return (tuple(i_alpha), frozenset(flat_words), tuple(_num_pairs(flat_words)),
            frozenset(skeleton(" ".join(words)).split()), script_of(" ".join(i_alpha)))


@lru_cache(maxsize=65536)
def _route_side(route: str) -> tuple:
    g_alpha, g_nums = _core(norm(route).split())
    return (tuple(g_alpha), tuple(g_nums), tuple(_num_pairs(norm(route).split())), frozenset(skeleton(route).split()),
            script_of(" ".join(g_alpha)))


def route_match(route: str, text: str, pc_re: re.Pattern | None = None) -> str:
    """geo 路名 vs 原文道路段：CONFIRMED / CORRECTED / CONFLICT / INFERRED（原文没写路名）。"""
    i_alpha, all_nums, tp, sk_i, si = _text_side(text, pc_re)
    g_alpha, g_nums, rp, sk_g, sg = _route_side(route)
    if g_nums and not all(n in all_nums for n in g_nums):
        return "CONFLICT"  # 编号道路号码不一致（海湾国家 Road / Block 号写在别的段里也算）
    if not g_alpha:
        if not g_nums:
            return "INFERRED"
        if rp and tp:  # 编号道路：每个"类型 + 号码"都要在原文里；号码在、类型不同（Avenue / Road 2833）算纠正
            nums = {n for _, n in tp}
            if any(x not in tp and x[1] not in nums for x in rp):
                return "CONFLICT"  # 7، شارع 10 ≠ شارع 7（门牌和街道号对调）
            return "CONFIRMED" if all(x in tp for x in rp) else "CORRECTED"
        return "CONFIRMED"
    if not i_alpha:
        return "INFERRED"
    if si != sg:  # 两边文字不同：阿拉伯文 <-> 拉丁转写按整串辅音骨架比；其他文字之间（泰文 / 拉丁）无从比较
        if {si, sg} != {"arabic", "latin"}:
            return "INFERRED"
        a, b = skeleton(" ".join(g_alpha)), skeleton(" ".join(i_alpha))
        return "CORRECTED" if a and b and fuzz.token_set_ratio(a, b) >= 85 else "CONFLICT"
    blob_i, blob_g = " " + " ".join(i_alpha), " " + " ".join(g_alpha)
    g_hits = [_hit(w, i_alpha, sk_i, blob_i) for w in g_alpha]
    i_hits = [_hit(w, g_alpha, sk_g, blob_g) for w in i_alpha]
    g_cov = sum(bool(h) for h in g_hits) / len(g_alpha)
    i_cov = sum(bool(h) for h in i_hits) / len(i_alpha)
    exact = all(h in ("exact", "") for h in g_hits + i_hits)
    # geo 路名的词全在原文路名里（原文多出的是楼名 / 描述），或原文的词全在 geo 路名里、geo 至少一半对上（只写姓）
    if g_cov == 1 or (i_cov == 1 and g_cov >= 0.5):
        return "CONFIRMED" if exact else "CORRECTED"
    if g_cov >= 1 / 3 and i_cov >= 0.5:
        return "CORRECTED"
    return "CONFLICT"


def numbered_only(route: str) -> bool:
    """路名只是编号（شارع 18、Street 7、Calle 16）：同一城市里常有很多条，光凭路名和门牌定不了是哪一条。"""
    g_alpha, g_nums = _core(norm(route).split())
    return bool(g_nums) and not g_alpha
