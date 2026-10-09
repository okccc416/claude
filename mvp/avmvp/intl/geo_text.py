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
_SEG = re.compile(r"\s*(?:[,;|\n،]|\s[-–—]\s)\s*")
_HOUSE = re.compile(r"(?<![\dA-Z])\d{1,4}[A-Z]?(?:[/\-]\d{1,4}[A-Z]?)?(?![\dA-Z\-])")  # 5 位以上多是邮编


# 路名里常见的缩写（方位、圣人、军衔 / 称谓），两边统一成全称再比
ABBR = {"NTE": "NORTE", "OTE": "ORIENTE", "PTE": "PONIENTE", "STA": "SANTA", "STO": "SANTO", "SRA": "SENHORA",
        "SR": "SENHOR", "GRAL": "GENERAL", "GEN": "GENERAL", "CEL": "CORONEL", "CNEL": "CORONEL", "TTE": "TENIENTE",
        "PDTE": "PRESIDENTE", "PRES": "PRESIDENTE", "STR": "STR", "NSRA": "SENHORA", "PROF": "PROFESSOR",
        "ENG": "ENGENHEIRO", "ING": "INGENIERO", "LIC": "LICENCIADO", "MCAL": "MARISCAL", "ALM": "ALMIRANTE"}


def _canon(w: str) -> str:
    """缩写展开；德 / 荷式粘连类型词统一：MARTINUSSTRASSE / MARTINUSSTR / MERESTRAAT -> …STR。"""
    w = ABBR.get(w, w)
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
    segs = [s for s in _SEG.split(fold(text)) if s.strip()]
    if not segs:
        return [], [], set()
    plain = [pc_re.sub(" ", s) if pc_re else s for s in segs]  # 去掉邮编再找门牌
    i = next((k for k, s in enumerate(plain) if _HOUSE.search(s)), 0)  # 第一个带门牌号的段
    street = [i]
    if not _core(norm(plain[i]).split())[0] and len(segs) > 1:
        street.append(i - 1 if i > 0 else i + 1)  # 门牌号单独成段：路名在前一段（C/ Joaquín Peralta, 12）或后一段
    words = [w for k in sorted(street) for w in norm(plain[k]).split()]
    toks = norm(plain[i]).split()
    nums = [k for k, w in enumerate(toks) if re.fullmatch(r"\d{1,4}[A-Z]?", w)]
    if not nums or len(street) > 1:
        name = words
    elif nums[0] == 0:
        name = toks[1:]
    else:
        name = toks[:nums[-1]]
    other = {w for k, s in enumerate(segs) if k not in street for w in norm(s).split()}
    return words, name, other - set(words)


def _hit(w: str, pool: list[str], skel: set[str], blob: str) -> str:
    """一个词在另一边的对应："exact" / "fuzzy" / ""。"""
    if w in pool:
        return "exact"
    if len(w) >= 4 and f" {w}" in blob:  # 泰文等不分词的文字；粘连写法
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


def route_match(route: str, text: str, pc_re: re.Pattern | None = None) -> str:
    """geo 路名 vs 原文道路段：CONFIRMED / CORRECTED / CONFLICT / INFERRED（原文没写路名）。"""
    words, name, locality = street_part(text, pc_re)
    g_alpha, g_nums = _core(norm(route).split())
    i_alpha, i_nums = _core(name)
    if locality and [w for w in i_alpha if w not in locality]:
        i_alpha = [w for w in i_alpha if w not in locality]  # 道路段里夹着的城镇名不算路名（只剩城镇名时保留）
    all_nums = set(norm(pc_re.sub(" ", fold(text)) if pc_re else text).split())
    if g_nums and not all(n in all_nums for n in g_nums):
        return "CONFLICT"  # 编号道路号码不一致（海湾国家 Road / Block 号写在别的段里也算）
    if not g_alpha:
        return "CONFIRMED" if g_nums else "INFERRED"
    if not i_alpha:
        return "INFERRED"
    si, sg = script_of(" ".join(i_alpha)), script_of(" ".join(g_alpha))
    if si != sg:  # 两边文字不同：阿拉伯文 <-> 拉丁转写按整串辅音骨架比；其他文字之间（泰文 / 拉丁）无从比较
        if {si, sg} != {"arabic", "latin"}:
            return "INFERRED"
        a, b = skeleton(" ".join(g_alpha)), skeleton(" ".join(i_alpha))
        return "CORRECTED" if a and b and fuzz.token_set_ratio(a, b) >= 85 else "CONFLICT"
    blob_i, blob_g = " " + " ".join(i_alpha), " " + " ".join(g_alpha)
    sk_i, sk_g = set(skeleton(" ".join(words)).split()), set(skeleton(route).split())
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
