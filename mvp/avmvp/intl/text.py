"""多语种文本规范化：把各市场的地址文字映射成统一的"匹配键"。

- 数字：阿拉伯-印度数字、波斯数字、泰文数字 -> 0-9
- 拉丁字母：去掉声调 / 重音（越南语 Nguyễn -> NGUYEN，德语 ß -> SS，Đ -> D），转大写
- 阿拉伯文：统一 أ إ آ -> ا、ة -> ه、ى -> ي，去掉元音符号和延长线
- 泰文：没有空格，用 PyThaiNLP 词典分词（离线）
- 缩写：按市场展开（Jl. -> JALAN、Str. -> STRASSE、Q.1 -> QUAN 1 …）
- 道路 / 片区类型词：另生成去掉类型词的"核心键"，用于容忍"写没写 Jalan / Đường / Rue"的差异
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹๐๑๒๓๔๕๖๗๘๙", "0123456789" * 3)
_AR_DIACRITICS = re.compile(r"[ً-ٰٟـ]")
_AR_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي", "ـ": ""})
_THAI = re.compile(r"[฀-๿]")
_ARABIC = re.compile(r"[؀-ۿ]")
_TOKEN = re.compile(r"[฀-๿]+|[؀-ۿ]+|[A-Z0-9]+(?:[/\-][A-Z0-9]+)*|#", re.I)

# 各市场的缩写 / 变体 -> 规范写法（作用在单个词上）
ABBREV: dict[str, dict[str, str]] = {
    "EN": {"ST": "STREET", "STR": "STREET", "RD": "ROAD", "AVE": "AVENUE", "AV": "AVENUE", "DR": "DRIVE",
           "DRV": "DRIVE", "PL": "PLACE", "LN": "LANE", "CRES": "CRESCENT", "CR": "CRESCENT", "CT": "COURT",
           "PDE": "PARADE", "HWY": "HIGHWAY", "BLVD": "BOULEVARD", "TCE": "TERRACE", "TER": "TERRACE", "CL": "CLOSE",
           "SQ": "SQUARE", "CCT": "CIRCUIT", "GR": "GROVE", "GRV": "GROVE", "WY": "WAY", "ESP": "ESPLANADE",
           "N": "NORTH", "NTH": "NORTH", "S": "SOUTH", "STH": "SOUTH", "E": "EAST", "W": "WEST", "MT": "MOUNT",
           "HTS": "HEIGHTS", "PKWY": "PARKWAY", "RDGE": "RIDGE", "BVD": "BOULEVARD", "APT": "APARTMENT",
           "BLDG": "BUILDING", "TWR": "TOWER", "FLR": "FLOOR", "LVL": "LEVEL", "UPR": "UPPER", "LWR": "LOWER",
           "STO": "SANTO", "STA": "SANTA", "GEN": "GENERAL", "BRGY": "BARANGAY", "BGY": "BARANGAY",
           "EXT": "EXTENSION", "PRES": "PRESIDENT"},
    "DE": {"STR": "STRASSE", "STRAßE": "STRASSE", "PL": "PLATZ", "STRASE": "STRASSE"},
    "FR": {"R": "RUE", "AV": "AVENUE", "AVE": "AVENUE", "BD": "BOULEVARD", "BLVD": "BOULEVARD", "PL": "PLACE",
           "ST": "SAINT", "STE": "SAINTE", "QU": "QUAI", "IMP": "IMPASSE", "CHE": "CHEMIN", "SQ": "SQUARE",
           "FG": "FAUBOURG", "FBG": "FAUBOURG", "PASS": "PASSAGE", "ALL": "ALLEE", "CRS": "COURS"},
    "NL": {"STR": "STRAAT", "PLN": "PLEIN"},
    "MY": {"JLN": "JALAN", "JL": "JALAN", "LOR": "LORONG", "LRG": "LORONG", "PSN": "PERSIARAN", "LBH": "LEBUH",
           "TMN": "TAMAN", "BDR": "BANDAR", "KG": "KAMPUNG", "KPG": "KAMPUNG", "BT": "BUKIT", "BKT": "BUKIT",
           "SG": "SUNGAI", "SGI": "SUNGAI", "MDN": "MEDAN", "SEK": "SEKSYEN", "PSRN": "PERSIARAN", "PJ": "PETALING JAYA", "KL": "KUALA LUMPUR", "WP": "WILAYAH PERSEKUTUAN"},
    "ID": {"JL": "JALAN", "JLN": "JALAN", "GG": "GANG", "NO": "NOMOR", "KEL": "KELURAHAN", "KEC": "KECAMATAN",
           "KAV": "KAVLING", "BLK": "BLOK", "RY": "RAYA", "KOMP": "KOMPLEK", "PERUM": "PERUMAHAN",
           # 人名头衔与方位（参考库里全称、缩写混用，两边统一成全称）
           "DR": "DOKTER", "LETJEN": "LETNAN JENDERAL", "MAYJEN": "MAYOR JENDERAL", "BRIGJEN": "BRIGADIR JENDERAL",
           "JEND": "JENDERAL", "KOL": "KOLONEL", "PROF": "PROFESOR", "IR": "INSINYUR", "PANG": "PANGERAN",
           "TIM": "TIMUR", "BAR": "BARAT", "SEL": "SELATAN", "UTR": "UTARA"},
    "TH": {"ถ": "ถนน", "ซ": "ซอย", "RD": "ROAD", "SOI": "ซอย", "THANON": "ถนน", "KHWAENG": "แขวง", "KHET": "เขต",
           "ต": "ตำบล", "อ": "อำเภอ", "จ": "จังหวัด"},
    "VN": {"D": "DUONG", "P": "PHUONG", "Q": "QUAN", "TP": "THANH PHO", "H": "HUYEN", "KP": "KHU PHO",
           "HCM": "HO CHI MINH", "HCMC": "HO CHI MINH", "TPHCM": "THANH PHO HO CHI MINH", "HEM": "HEM"},
    "AR": {"ST": "STREET", "RD": "ROAD", "AL": "AL", "EL": "AL"},
}
# 道路 / 片区的类型词：核心键里去掉（写没写都能匹配上）
TYPE_WORDS: dict[str, set[str]] = {
    "EN": {"STREET", "ROAD", "AVENUE", "DRIVE", "PLACE", "LANE", "CRESCENT", "COURT", "PARADE", "HIGHWAY",
           "BOULEVARD", "TERRACE", "CLOSE", "SQUARE", "CIRCUIT", "GROVE", "WAY", "ESPLANADE", "PARKWAY"},
    "DE": {"STRASSE", "PLATZ", "WEG", "ALLEE", "DAMM", "UFER", "RING", "CHAUSSEE", "STEIG", "PFAD", "GASSE"},
    "FR": {"RUE", "AVENUE", "BOULEVARD", "PLACE", "QUAI", "IMPASSE", "CHEMIN", "SQUARE", "PASSAGE", "ALLEE",
           "COURS", "VILLA", "CITE", "FAUBOURG", "DE", "DU", "DES", "LA", "LE", "L", "D"},
    "NL": set(),
    "MY": {"JALAN", "LORONG", "PERSIARAN", "LEBUH", "LEBUHRAYA"},
    "ID": {"JALAN", "GANG", "RAYA"},
    "TH": {"ถนน", "ซอย", "ROAD", "SOI"},
    "VN": {"DUONG", "HEM", "PHO"},
    "AR": {"شارع", "طريق", "STREET", "ROAD", "AL", "ال"},
    "AREA": {"DISTRICT", "SUBDISTRICT", "CITY", "حي", "KELURAHAN", "KECAMATAN", "แขวง", "เขต", "ตำบล", "อำเภอ",
             "PHUONG", "QUAN", "HUYEN", "TAMAN", "BANDAR", "KAMPUNG", "BARANGAY", "BRGY", "BGY"},
}
MARKET_LANG = {"AU": "EN", "PH": "EN", "AE": "AR", "SA": "AR", "DE": "DE", "FR": "FR", "NL": "NL", "MY": "MY",
               "ID": "ID", "TH": "TH", "VN": "VN", "SG": "EN"}


def fold(text: str) -> str:
    """数字统一、去重音、阿拉伯文字形统一、转大写。"""
    t = unicodedata.normalize("NFKC", text).translate(_DIGITS)
    t = t.replace("ß", "SS").replace("đ", "d").replace("Đ", "D")
    if _ARABIC.search(t):
        t = _AR_DIACRITICS.sub("", t).translate(_AR_MAP)
    # 去掉拉丁字母上的附加符号（泰文的元音符号也是组合字符，不能去）
    t = "".join(c for c in unicodedata.normalize("NFD", t)
                if not (unicodedata.combining(c) and not _THAI.match(c)))
    return unicodedata.normalize("NFC", t).upper()


@lru_cache(maxsize=1)
def _thai_tokenizer():
    try:
        from pythainlp.tokenize import word_tokenize
        return lambda s: [w for w in word_tokenize(s, engine="newmm") if w.strip()]
    except ImportError:  # 没装 PyThaiNLP 时按整段处理
        return lambda s: [s]


def tokenize(text: str) -> list[str]:
    """分词：拉丁 / 数字按空格和标点切开（保留 339/5、12-14 这类门牌），泰文用词典分词。"""
    out: list[str] = []
    t = fold(text)
    t = re.sub(r"(?<=\d)(?=[A-Z]{3,})(?!(?:ST|ND|RD|TH|HS|BG|BV)\b)", " ", t)  # 500OXFORD -> 500 OXFORD
    t = re.sub(r"\b(SHOP|UNIT|LEVEL|SUITE|LOT|BLOCK|BLK|OFFICE)(?=\d)", r"\1 ", t)  # SHOP4068 -> SHOP 4068
    for m in _TOKEN.finditer(t):
        tok = m.group(0)
        if _THAI.match(tok):
            out.extend(_thai_tokenizer()(tok))
        elif tok == "#" or re.fullmatch(r"\d+(?:[/\-]\d+)*[A-Z]?|[A-Z]+", tok):
            out.append(tok)
        else:  # 字母数字混合且带连字符 / 斜杠：Karl-Marx -> KARL MARX；18/61、1/68F 保留
            out.extend(p for p in re.split(r"-(?=[A-Z])|(?<=[A-Z])-|(?<=[A-Z])/(?=\d)|(?<=\d)/(?=[A-Z]{2})", tok) if p)
    return out


def expand(tokens: list[str], market: str) -> list[str]:
    table = ABBREV.get(MARKET_LANG.get(market, "EN"), {})
    base = ABBREV["EN"] if MARKET_LANG.get(market) in ("EN", "AR") else {}
    out = []
    for t in _merge_initials(tokens):
        if market == "DE" and len(t) > 4 and t.endswith("STR"):
            t = t + "ASSE"  # Yorckstr. -> YORCKSTRASSE
        if market == "TH" and len(t) > 2 and t[:3] in ("ซอย", "ถนน") and t not in ("ซอย", "ถนน"):
            out.extend([t[:3], t[3:]])  # ซอยร่วมพัฒนา -> ซอย ร่วมพัฒนา
            continue
        e = table.get(t) or base.get(t) or t
        out.extend(e.split())
    return out


def _merge_initials(tokens: list[str]) -> list[str]:
    """连续的单个拉丁字母合并：M.H. Thamrin / M H Thamrin -> MH THAMRIN（人名缩写写法不一）。"""
    out: list[str] = []
    run: list[str] = []
    for t in tokens + [""]:
        if len(t) == 1 and "A" <= t <= "Z":
            run.append(t)
            continue
        out.extend(["".join(run)] if len(run) >= 2 else run)
        run = []
        if t:
            out.append(t)
    return out


def merge_initials(text: str) -> str:
    return " ".join(_merge_initials(text.split()))


def key(text: str, market: str) -> str:
    """完整匹配键：规范化 + 缩写展开。"""
    return " ".join(expand(tokenize(text), market))


def core_key(text: str, market: str, kind: str = "street") -> str:
    """核心键：再去掉类型词（Jalan / Đường / Rue / شارع …），全部是类型词时保留原样。"""
    toks = key(text, market).split()
    drop = TYPE_WORDS["AREA"] if kind == "area" else TYPE_WORDS.get(MARKET_LANG.get(market, "EN"), set())
    kept = [t for t in toks if t not in drop]
    if MARKET_LANG.get(market) == "AR":
        kept = [t[2:] if t.startswith("ال") and len(t) > 3 else t for t in kept]  # 去掉阿拉伯文冠词 ال
    return " ".join(kept) if kept else " ".join(toks)


# ---------------------------------------------------------------------------------------------- 转写骨架
# 阿拉伯文与拉丁转写（Ibn Taymiyyah St. <-> شارع ابن تيمية）只比较辅音骨架：长元音 / 半元音 ا و ي ى ة ء ع 与
# 拉丁元音 A E I O U W Y 都去掉，发音相近的辅音合并（ث/ت -> T，ق/ك -> K，ج/غ -> J …），重复辅音合并，词尾 H 去掉。
_AR_SKEL = {"ب": "B", "ت": "T", "ث": "T", "ج": "J", "ح": "H", "خ": "K", "د": "D", "ذ": "D", "ر": "R", "ز": "Z",
            "س": "S", "ش": "S", "ص": "S", "ض": "D", "ط": "T", "ظ": "Z", "غ": "J", "ف": "F", "ق": "K", "ك": "K",
            "ل": "L", "م": "M", "ن": "N", "ه": "H", "پ": "B", "چ": "J", "گ": "J", "ڤ": "F"}
_LAT_SKEL = [("KH", "K"), ("SH", "S"), ("TH", "T"), ("DH", "D"), ("GH", "J"), ("PH", "F"), ("CH", "S"), ("Q", "K"),
             ("C", "K"), ("G", "J"), ("X", "KS"), ("V", "F"), ("P", "B"), ("OU", "W")]
_LAT_WORDS = {"KING": "MALIK", "PRINCE": "AMIR", "PRINCESS": "AMIRA", "SAINT": "", "HAY": "", "HAYY": ""}
_ARTICLES = {"AL", "EL", "AS", "AT", "ATH", "AD", "ADH", "AN", "AR", "AZ", "ASH", "ASS", "UL", "UD", "US", "UR",
             "UN", "UZ", "UT", "ULL"}
_SKEL_DROP = {"STREET", "ST", "ROAD", "RD", "AVENUE", "AVE", "DISTRICT", "SQUARE", "HIGHWAY", "LANE", "شارع", "طريق", "حي",
              "ميدان"}


def skeleton(text: str) -> str:
    """转写骨架（只用于阿拉伯文市场的道路 / 片区容错召回）。"""
    out = []
    for w in fold(text).replace("-", " ").split():
        w = re.sub(r"[^A-Z؀-ۿ]", "", w)
        if not w or w in _SKEL_DROP or w in _ARTICLES:
            continue
        if _ARABIC.search(w):
            if w.startswith("ال") and len(w) > 3:
                w = w[2:]
            sk = "".join(_AR_SKEL.get(c, "") for c in w)
        else:
            w = _LAT_WORDS.get(w, w)
            for x, y in _LAT_SKEL:
                w = w.replace(x, y)
            sk = re.sub(r"[AEIOUWY]", "", w)
        sk = sk[:-1] if sk.endswith("H") and len(sk) > 2 else sk
        out.append(sk)
    return re.sub(r"(.)\1+", r"\1", "".join(out))


def script_of(text: str) -> str:
    if _ARABIC.search(text):
        return "arabic"
    if _THAI.search(text):
        return "thai"
    return "latin"
