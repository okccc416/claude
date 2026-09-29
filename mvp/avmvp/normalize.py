"""预处理：统一大小写、标点、缩写，生成用于匹配的"规范键"（match key）。

核心思路：输入和参考库两边都映射到同一套缩写形式再比较，
例如 "Ang Mo Kio Avenue 3" 与 "ang mo kio ave 3" 的规范键都是 "ANG MO KIO AVE 3"。
这样既不用猜 "ST" 是 Street 还是 Saint（两边都映射成 ST），也不会误改用户原文。
"""

from __future__ import annotations

import re
import unicodedata

# 规范缩写 -> 该缩写的所有常见写法（新加坡街道与楼宇常用词）
_VARIANTS: dict[str, tuple[str, ...]] = {
    "AVE": ("AVENUE", "AVE", "AV", "AVN"),
    "ST": ("STREET", "ST", "STR", "SAINT"),
    "RD": ("ROAD", "RD"),
    "DR": ("DRIVE", "DR", "DRV"),
    "CRES": ("CRESCENT", "CRES", "CRESC"),
    "CL": ("CLOSE", "CL"),
    "LN": ("LANE", "LN"),
    "BLVD": ("BOULEVARD", "BLVD"),
    "CTRL": ("CENTRAL", "CTRL", "CTL"),
    "NTH": ("NORTH", "NTH"),
    "STH": ("SOUTH", "STH"),
    "JLN": ("JALAN", "JLN", "JL"),
    "LOR": ("LORONG", "LOR", "LRG"),
    "BT": ("BUKIT", "BT", "BKT"),
    "UPP": ("UPPER", "UPP", "UPR"),
    "TG": ("TANJONG", "TANJUNG", "TG"),
    "KG": ("KAMPONG", "KAMPUNG", "KG"),
    "TER": ("TERRACE", "TER", "TERR"),
    "PL": ("PLACE", "PL"),
    "PK": ("PARK", "PK"),
    "HTS": ("HEIGHTS", "HTS"),
    "GDNS": ("GARDENS", "GDNS"),
    "GDN": ("GARDEN", "GDN"),
    "IND": ("INDUSTRIAL", "IND"),
    "SQ": ("SQUARE", "SQ"),
    "MT": ("MOUNT", "MT"),
    "CIR": ("CIRCLE", "CIR"),
    "EST": ("ESTATE", "EST"),
    "GR": ("GROVE", "GR", "GRV"),
    "EXPWY": ("EXPRESSWAY", "EXPWY"),
    "CTR": ("CENTRE", "CENTER", "CTR"),
    "BLDG": ("BUILDING", "BLDG"),
    "TWR": ("TOWER", "TWR"),
    "APT": ("APARTMENT", "APARTMENTS", "APT", "APTS"),
}

ABBREV: dict[str, str] = {v: k for k, vs in _VARIANTS.items() for v in vs}

# 可做拼写纠错的"路型词"全称（≥ 5 个字母的词 + 最常见的 ROAD / LANE / PARK；更短的词纠错误伤太大）
ROAD_TYPE_WORDS: dict[str, str] = {
    vs[0]: k for k, vs in _VARIANTS.items()
    if (len(vs[0]) >= 5 or vs[0] in ("ROAD", "LANE", "PARK"))
    and k not in ("CTR", "BLDG", "TWR", "APT", "EST", "GDN", "SQ", "MT")
}

# 新加坡本地的市镇缩写（AMK Ave 3 = Ang Mo Kio Avenue 3）。两字母缩写容易撞车，只在后面紧跟路型 / 方位词时展开
TOWN_ABBREV: dict[str, str] = {
    "AMK": "ANG MO KIO", "CCK": "CHOA CHU KANG", "TPY": "TOA PAYOH", "BTB": "BUKIT BATOK", "BTP": "BUKIT PANJANG",
    "TAMP": "TAMPINES", "TPN": "TAMPINES", "WDL": "WOODLANDS", "SBW": "SEMBAWANG", "SRG": "SERANGOON",
    "SKG": "SENGKANG", "PGL": "PUNGGOL", "CWEALTH": "COMMONWEALTH",
    "BB": "BUKIT BATOK", "BP": "BUKIT PANJANG", "JW": "JURONG WEST", "JE": "JURONG EAST", "PR": "PASIR RIS",
    "SK": "SENGKANG", "PG": "PUNGGOL", "HG": "HOUGANG", "YS": "YISHUN", "WL": "WOODLANDS",
}
_TOWN_CONTEXT = {"ST", "AVE", "DR", "CTRL", "NTH", "STH", "EAST", "WEST", "RD", "CRES", "IND", "RING", "WAY",
                 "WALK", "LINK", "CL", "LN", "RISE", "VIEW", "LOOP", "PL", "NORTH", "SOUTH"}

# 楼栋号前缀标记
BLOCK_MARKERS = {"BLK", "BLOCK", "NO", "NUMBER"}
# 国家名等噪声词（仅在首尾或邮编旁出现时剔除）
COUNTRY_TOKENS = {"SINGAPORE", "SPORE", "SG"}  # 注意不能收 SIN：Sin Ming Road 等路名以 SIN 开头

_APOSTROPHES = re.compile(r"[’'`]")
_PUNCT = re.compile(r"[,.;:()\[\]{}\"/\\|]+")
_SPACES = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """Unicode 规范化 + 大写 + 去撇号。保留 # 和 -，供单元号解析使用。"""
    text = unicodedata.normalize("NFKC", text or "").upper()
    text = _APOSTROPHES.sub("", text)
    return _SPACES.sub(" ", text).strip()


def strip_punct(text: str) -> str:
    text = re.sub(r"(?<=[A-Z]{2})(?=\d)", " ", text)  # BLK123 / AVE3 / BIZ1 -> BLK 123 / AVE 3 / BIZ 1（两边一致）
    text = _PUNCT.sub(" ", text)
    text = re.sub(r"(?<=\d)-(?=\d)", "\x00", text)  # 保留数字之间的连字符：楼栋号 188-2B
    text = text.replace("-", " ").replace("#", " ").replace("\x00", "-")
    return _SPACES.sub(" ", text).strip()


def canon_tokens(tokens: list[str]) -> list[str]:
    out: list[str] = []
    for i, t in enumerate(tokens):
        c = ABBREV.get(t, t)
        town = TOWN_ABBREV.get(c)
        nxt = ABBREV.get(tokens[i + 1], tokens[i + 1]) if i + 1 < len(tokens) else None
        if town and (len(c) >= 3 or nxt in _TOWN_CONTEXT):
            out.extend(ABBREV.get(w, w) for w in town.split())
        else:
            out.append(c)
    return out


def match_key(text: str) -> str:
    """把任意文本（参考库或用户输入）映射为规范匹配键。"""
    return " ".join(canon_tokens(strip_punct(clean_text(text)).split()))


def split_alpha_num(key: str) -> tuple[str, tuple[str, ...]]:
    """拆成字母部分和数字部分：'ANG MO KIO AVE 3' -> ('ANG MO KIO AVE', ('3',))。

    数字部分必须精确相等才算同一条路——"AVE 3" 和 "AVE 5" 字面很像，但是两条不同的路。
    """
    alpha, nums = [], []
    for t in key.split():
        (nums if any(c.isdigit() for c in t) else alpha).append(t)
    return " ".join(alpha), tuple(nums)


def title_case(text: str) -> str:
    """输出用的标题格式：保留数字+字母（如 11A）为大写。"""
    out = []
    for t in text.split():
        out.append(t if any(c.isdigit() for c in t) else t.capitalize())
    return " ".join(out)
