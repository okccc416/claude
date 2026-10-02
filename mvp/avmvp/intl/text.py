"""多语种文本规范化：把各市场的地址文字映射成统一的"匹配键"。

- 数字：阿拉伯-印度数字、波斯数字、泰文数字 -> 0-9
- 拉丁字母：去掉声调 / 重音（越南语 Nguyễn -> NGUYEN，德语 ß -> SS，Đ -> D），转大写
- 阿拉伯文：统一 أ إ آ -> ا、ة -> ه、ى -> ي，去掉元音符号和延长线
- 泰文：没有空格，用 PyThaiNLP 词典分词（离线）
- 西里尔文（保加利亚）：按官方转写规则转成拉丁字母（ул. Пиротска -> UL PIROTSKA），与拉丁转写的输入对得上
- 日文：町丁目 + 番地-号统一成"町名 N CHOME 番地-号"（丸の内2丁目7番9号 / 丸の内2-7-9 / 2 Chome-7-9 Marunouchi）
- 波兰文 ł、丹麦 / 挪威文 ø æ 等不能分解的字母：映射成基本拉丁字母
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
_CJK_CHARS = "\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff々〆ヶ"
_CJK = re.compile(f"[{_CJK_CHARS}]")
_TOKEN = re.compile(f"[฀-๿]+|[؀-ۿ]+|[{_CJK_CHARS}]+|[A-Z0-9]+(?:[/\\-][A-Z0-9]+)*|#", re.I)
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
# 保加利亚官方转写（2009 年《转写法》）；俄文字母按常见写法
_CYR = dict(zip("АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЬЮЯЁЫЭ",
                ["A", "B", "V", "G", "D", "E", "ZH", "Z", "I", "Y", "K", "L", "M", "N", "O", "P", "R", "S", "T", "U",
                 "F", "H", "TS", "CH", "SH", "SHT", "A", "Y", "YU", "YA", "YO", "Y", "E"]))
_CYR.update({k.lower(): v.lower() for k, v in _CYR.items()})
_CYR_MAP = str.maketrans(_CYR)
# NFD 分解不了的拉丁字母
_LATIN_EXTRA = str.maketrans({"ł": "l", "Ł": "L", "ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE", "œ": "oe", "Œ": "OE",
                              "ı": "i", "ð": "d", "Ð": "D", "þ": "th", "Þ": "TH", "ħ": "h", "Ħ": "H"})
# 意大利文带点缩写（V.le / C.so / P.za / P.zza / P.le / L.go / F.lli），拆词前整体换掉
_IT_DOTTED = [(re.compile(r"\bV\.\s?LE\b"), "VIALE"), (re.compile(r"\bC\.\s?SO\b"), "CORSO"),
              (re.compile(r"\bP\.\s?Z?ZA\b"), "PIAZZA"), (re.compile(r"\bP\.\s?LE\b"), "PIAZZALE"),
              (re.compile(r"\bL\.\s?GO\b"), "LARGO"), (re.compile(r"\bF\.\s?LLI\b"), "FRATELLI")]

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
    "ES": {"C": "CALLE", "CL": "CALLE", "CLL": "CALLE", "CALL": "CALLE", "AV": "AVENIDA", "AVE": "AVENIDA",
           "AVDA": "AVENIDA", "AVD": "AVENIDA", "PS": "PASEO", "PSO": "PASEO", "PZA": "PLAZA", "PL": "PLAZA",
           "PLZ": "PLAZA", "CTRA": "CARRETERA", "CRTA": "CARRETERA", "CARR": "CARRETERA", "CMNO": "CAMINO",
           "CAM": "CAMINO", "GTA": "GLORIETA", "RDA": "RONDA", "TRV": "TRAVESIA", "TRAV": "TRAVESIA",
           "CALZ": "CALZADA", "BLVD": "BOULEVARD", "BLV": "BOULEVARD", "BV": "BOULEVARD", "PJE": "PASAJE",
           "PSJE": "PASAJE", "CDA": "CERRADA", "PRIV": "PRIVADA", "PROL": "PROLONGACION", "CJON": "CALLEJON",
           "DIAG": "DIAGONAL", "DG": "DIAGONAL", "TV": "TRANSVERSAL", "TR": "TRANSVERSAL", "TRANSV": "TRANSVERSAL",
           "KR": "CARRERA", "KRA": "CARRERA", "CRA": "CARRERA", "CR": "CARRERA", "CRR": "CARRERA",
           "AK": "AVENIDA CARRERA", "AC": "AVENIDA CALLE", "NO": "NUMERO", "NUM": "NUMERO", "NRO": "NUMERO",
           "COL": "COLONIA", "FRACC": "FRACCIONAMIENTO", "URB": "URBANIZACION", "BO": "BARRIO", "GRAL": "GENERAL",
           "GRL": "GENERAL", "STA": "SANTA", "STO": "SANTO", "PDTE": "PRESIDENTE", "PTE": "PONIENTE",
           "OTE": "ORIENTE", "NTE": "NORTE", "DR": "DOCTOR", "ING": "INGENIERO", "LIC": "LICENCIADO",
           "PROF": "PROFESOR", "CNEL": "CORONEL", "TTE": "TENIENTE", "ALM": "ALMIRANTE", "MCAL": "MARISCAL",
           "EDIF": "EDIFICIO", "ED": "EDIFICIO", "OF": "OFICINA", "OFIC": "OFICINA", "DEPTO": "DEPARTAMENTO",
           "DPTO": "DEPARTAMENTO", "LOC": "LOCAL", "INT": "INTERIOR"},
    "PT": {"R": "RUA", "AV": "AVENIDA", "AVEN": "AVENIDA", "AL": "ALAMEDA", "TV": "TRAVESSA", "TRAV": "TRAVESSA",
           "PC": "PRACA", "PCA": "PRACA", "PRC": "PRACA", "LG": "LARGO", "LGO": "LARGO", "EST": "ESTRADA",
           "ESTR": "ESTRADA", "ROD": "RODOVIA", "CC": "CALCADA", "CALC": "CALCADA", "BC": "BECO", "PCT": "PRACETA",
           "ESC": "ESCADINHAS", "QTA": "QUINTA", "S": "SAO", "STA": "SANTA", "STO": "SANTO", "DR": "DOUTOR",
           "DRA": "DOUTORA", "ENG": "ENGENHEIRO", "PROF": "PROFESSOR", "GEN": "GENERAL", "GAL": "GENERAL",
           "CEL": "CORONEL", "BRIG": "BRIGADEIRO", "MAL": "MARECHAL", "PRES": "PRESIDENTE", "CONS": "CONSELHEIRO",
           "DEP": "DEPUTADO", "VER": "VEREADOR", "CMDT": "COMANDANTE", "CAP": "CAPITAO", "TEN": "TENENTE",
           "INF": "INFANTE", "NO": "NUMERO", "NUM": "NUMERO", "CJ": "CONJUNTO", "SL": "SALA", "LJ": "LOJA",
           "APTO": "APARTAMENTO", "AP": "APARTAMENTO", "BL": "BLOCO", "VL": "VILA", "JD": "JARDIM", "PQ": "PARQUE"},
    "IT": {"V": "VIA", "VLE": "VIALE", "VL": "VIALE", "CSO": "CORSO", "CS": "CORSO", "PZA": "PIAZZA",
           "PZZA": "PIAZZA", "PLE": "PIAZZALE", "LGO": "LARGO", "VC": "VICOLO", "VCL": "VICOLO", "STR": "STRADA",
           "S": "SAN", "STA": "SANTA", "FLLI": "FRATELLI", "N": "NUMERO", "INT": "INTERNO"},
    "DA": {"GL": "GAMMEL", "PL": "PLADS", "BLVD": "BOULEVARD", "ST": "STUEN", "SDR": "SONDRE", "NR": "NORRE",
           "VESTRE": "VESTRE"},
    "NO": {"GT": "GATE", "VN": "VEIEN", "PL": "PLASS", "ST": "SANKT"},
    "SV": {"G": "GATAN", "V": "VAGEN", "PL": "PLAN", "LGH": "LAGENHET", "S": "SANKT", "ST": "SANKT"},
    "FI": {"K": "KATU", "T": "TIE"},
    "ET": {"TN": "TANAV", "MNT": "MAANTEE", "PST": "PUIESTEE", "PL": "PLATS"},
    "LV": {"IEL": "IELA", "BULV": "BULVARIS", "PROSP": "PROSPEKTS", "LAUK": "LAUKUMS"},
    "LT": {"G": "GATVE", "PR": "PROSPEKTAS", "PRAN": "PROSPEKTAS", "AL": "ALEJA", "PL": "PLENTAS",
           "SKG": "SKERSGATVIS", "TAK": "TAKAS", "KRANT": "KRANTINE"},
    "PL": {"UL": "ULICA", "AL": "ALEJA", "PL": "PLAC", "OS": "OSIEDLE", "SKW": "SKWER", "BULW": "BULWAR",
           "WYB": "WYBRZEZE", "SW": "SWIETEGO", "GEN": "GENERALA", "KS": "KSIEDZA", "PROF": "PROFESORA",
           "MJR": "MAJORA", "PLK": "PULKOWNIKA", "KARD": "KARDYNALA", "MARSZ": "MARSZALKA", "BP": "BISKUPA",
           "DR": "DOKTORA", "LOK": "LOKAL"},
    "CS": {"NAM": "NAMESTI", "TR": "TRIDA", "UL": "ULICE", "NABR": "NABREZI", "SV": "SVATEHO"},
    "SK": {"NAM": "NAMESTIE", "UL": "ULICA", "NABR": "NABREZIE", "TR": "TRIEDA", "SV": "SVATEHO"},
    "HU": {"U": "UTCA", "KRT": "KORUT", "RKP": "RAKPART", "SGT": "SUGARUT", "LTP": "LAKOTELEP", "EM": "EMELET"},
    "SL": {"UL": "ULICA", "C": "CESTA"},
    "HR": {"UL": "ULICA", "AV": "AVENIJA"},
    "BG": {"UL": "ULITSA", "ULICA": "ULITSA", "BUL": "BULEVARD", "BULV": "BULEVARD", "BLVD": "BULEVARD",
           "BOULEVARD": "BULEVARD", "PL": "PLOSHTAD", "ZK": "ZHK", "ZH": "ZHK", "KV": "KVARTAL",
           "ST": "ULITSA", "STREET": "ULITSA", "SQ": "PLOSHTAD", "SQUARE": "PLOSHTAD", "SV": "SVETA"},
    "JA": {},
}
# 比利时：法文 + 荷兰文
ABBREV["BE"] = {**ABBREV["NL"], **ABBREV["FR"]}
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
    "ES": {"CALLE", "AVENIDA", "PASEO", "PLAZA", "CARRETERA", "CAMINO", "GLORIETA", "RONDA", "TRAVESIA", "CALZADA",
           "BOULEVARD", "BULEVAR", "PASAJE", "CERRADA", "PRIVADA", "PROLONGACION", "CALLEJON", "DIAGONAL",
           "TRANSVERSAL", "CARRERA", "AUTOPISTA", "VIA", "EJE", "CIRCUITO", "ANDADOR", "RETORNO", "DE", "DEL", "LA",
           "LAS", "LOS", "EL"},
    "PT": {"RUA", "AVENIDA", "ALAMEDA", "TRAVESSA", "PRACA", "LARGO", "ESTRADA", "RODOVIA", "CALCADA", "BECO",
           "PRACETA", "ESCADINHAS", "VIELA", "VIADUTO", "PASSAGEM", "VIA", "DE", "DA", "DO", "DAS", "DOS"},
    "IT": {"VIA", "VIALE", "CORSO", "PIAZZA", "PIAZZALE", "LARGO", "VICOLO", "STRADA", "PIAZZETTA", "VIALETTO",
           "GALLERIA", "BASTIONI", "ALZAIA", "RIPA", "CONTRADA", "SALITA", "DEL", "DELLA", "DEI", "DEGLI", "DELLE",
           "DELLO", "DI", "DA", "D"},
    "DA": {"VEJ", "GADE", "ALLE", "PLADS", "TORV", "STRAEDE", "BOULEVARD"},
    "NO": {"GATE", "GATA", "VEI", "VEIEN", "PLASS", "ALLE", "TORG", "BRYGGE"},
    "SV": {"GATAN", "VAGEN", "TORGET", "PLAN", "ALLEN", "BACKE", "GRAND"},
    "FI": {"KATU", "TIE", "KUJA", "POLKU", "AUKIO", "TORI", "GATAN", "VAGEN"},
    "ET": {"TANAV", "MAANTEE", "PUIESTEE", "TEE", "PLATS", "VALJAK", "POIK"},
    "LV": {"IELA", "BULVARIS", "GATVE", "LAUKUMS", "PROSPEKTS", "DAMBIS", "SKVERS", "SOSEJA", "LINIJA",
           "KRASTMALA"},
    "LT": {"GATVE", "PROSPEKTAS", "ALEJA", "PLENTAS", "SKERSGATVIS", "TAKAS", "AIKSTE", "KRANTINE"},
    "PL": {"ULICA", "ALEJA", "ALEJE", "PLAC", "OSIEDLE", "RONDO", "SKWER", "BULWAR", "WYBRZEZE", "DROGA", "TRAKT",
           "PASAZ", "ZAULEK"},
    "CS": {"NAMESTI", "TRIDA", "ULICE", "NABREZI", "SADY"},
    "SK": {"NAMESTIE", "ULICA", "TRIEDA", "NABREZIE", "CESTA"},
    "HU": {"UT", "UTCA", "TER", "KORUT", "RAKPART", "SOR", "SETANY", "KOZ", "FASOR", "LIGET", "SUGARUT", "LEJTO",
           "LEPCSO", "LAKOTELEP", "HID"},
    "SL": {"ULICA", "CESTA", "TRG", "NABREZJE", "POT", "STEZA", "BREG", "NASELJE"},
    "HR": {"ULICA", "TRG", "AVENIJA", "CESTA", "PUT", "PROLAZ", "ODVOJAK", "OBALA", "PRILAZ", "STUBE"},
    "BG": {"ULITSA", "BULEVARD", "PLOSHTAD", "ZHK", "KVARTAL"},
    "JA": set(),
    "AREA": {"DISTRICT", "SUBDISTRICT", "CITY", "حي", "KELURAHAN", "KECAMATAN", "แขวง", "เขต", "ตำบล", "อำเภอ",
             "PHUONG", "QUAN", "HUYEN", "TAMAN", "BANDAR", "KAMPUNG", "BARANGAY", "BRGY", "BGY",
             "COLONIA", "COL", "BARRIO", "URBANIZACION", "FRACCIONAMIENTO", "BAIRRO", "JARDIM", "VILA", "LOCALIDAD",
             "COMUNA", "ALCALDIA", "DELEGACION", "QUARTIER", "ARRONDISSEMENT", "BEZIRK", "KERULET", "DZIELNICA",
             "QUARTIERE", "MUNICIPIO", "ZHK", "KVARTAL", "LINNAOSA", "RAJONS", "SENIUNIJA"},
}
TYPE_WORDS["BE"] = TYPE_WORDS["FR"] | TYPE_WORDS["NL"]
MARKET_LANG = {"AU": "EN", "PH": "EN", "AE": "AR", "SA": "AR", "DE": "DE", "FR": "FR", "NL": "NL", "MY": "MY",
               "ID": "ID", "TH": "TH", "VN": "VN", "SG": "EN",
               "CA": "EN", "GB": "EN", "IE": "EN", "NZ": "EN", "IN": "EN", "PR": "ES", "MX": "ES", "AR": "ES",
               "CL": "ES", "CO": "ES", "ES": "ES", "BR": "PT", "PT": "PT", "IT": "IT", "AT": "DE", "CH": "DE",
               "LU": "FR", "BE": "BE", "DK": "DA", "NO": "NO", "SE": "SV", "FI": "FI", "EE": "ET", "LV": "LV",
               "LT": "LT", "PL": "PL", "CZ": "CS", "SK": "SK", "HU": "HU", "SI": "SL", "HR": "HR", "BG": "BG",
               "JP": "JA"}
EN_BASE = {"PR", "IN"}  # 这些市场在本语种缩写之外，也用英文缩写（Ave. / St. / Apt.）


def fold(text: str) -> str:
    """数字统一、去重音、阿拉伯文字形统一、西里尔文转写、日文町丁目统一、转大写。"""
    t = unicodedata.normalize("NFKC", text).translate(_DIGITS)
    t = t.replace("ß", "SS").replace("đ", "d").replace("Đ", "D").translate(_LATIN_EXTRA)
    if _ARABIC.search(t):
        t = _AR_DIACRITICS.sub("", t).translate(_AR_MAP)
    if _CYRILLIC.search(t):
        t = t.translate(_CYR_MAP)
    # 去掉拉丁字母上的附加符号（泰文的元音符号、日文的浊点也是组合字符，不能去）
    t = "".join(c for c in unicodedata.normalize("NFD", t)
                if not (unicodedata.combining(c) and not _THAI.match(c) and c not in "\u3099\u309a"))
    t = unicodedata.normalize("NFC", t).upper()
    if _CJK.search(t) or "CHOME" in t:
        t = _japanese(t)
    return t


# ---------------------------------------------------------------------------------------------- 日文
_KANJI_DIGIT = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_DASHES = "\\-‐‑‒–—―−－ー\uff70"


def _kanji_number(s: str) -> int:
    """一 ~ 九十九：二 -> 2、十二 -> 12、二十三 -> 23。"""
    if "十" not in s:
        return int("".join(str(_KANJI_DIGIT[c]) for c in s))
    a, _, b = s.partition("十")
    return (_KANJI_DIGIT[a] if a else 1) * 10 + (_KANJI_DIGIT[b] if b else 0)


def _japanese(t: str) -> str:
    """日文地址的町丁目 / 番地 / 号统一写法：

    丸の内二丁目7番9号、丸の内2丁目7-9、丸の内2-7-9、YURAKUCHO, 2 CHOME-7-1、2 CHOME-7-1 YURAKUCHO
    -> 丸の内 2CHOME 7-9 / YURAKUCHO 2CHOME 7-1；都道府县、市区单独成词（东京都 千代田区 丸の内 …）。
    """
    t = re.sub(f"(?<=\\d)[{_DASHES}](?=\\d)", "-", t)
    t = re.sub("([〇一二三四五六七八九十]+)(?=丁目)", lambda m: str(_kanji_number(m.group(1))), t)
    t = re.sub(r"(\d+)丁目\s*", r" \1CHOME ", t)
    t = re.sub(f"(\\d+)\\s*CHOME\\b[\\s{_DASHES}]*", r" \1CHOME ", t)
    t = re.sub(r"(\d+)番地?(?=\d)", r"\1-", t)
    t = re.sub(r"(\d+)番地?", r"\1 ", t)
    t = re.sub(r"(?<=\d)号", " ", t)
    t = re.sub(f"(?<=[{_CJK_CHARS}])(\\d{{1,2}})-(\\d+(?:-\\d+)?)", r" \1CHOME \2", t)  # 八重洲2-1、丸の内2-7-9
    t = re.sub(r"\b([A-Z]{3,}),?\s+(\d+CHOME)", r"\1 \2", t)  # YURAKUCHO, 2CHOME
    t = re.sub(r"(\d+CHOME)\s+(\d+(?:-\d+)*)\s+([A-Z]{4,})\b(?!\s(?:CITY|KU|WARD)\b)", r"\3 \1 \2", t)
    t = re.sub(r"(東京都|北海道|京都府|大阪府|[^\s\d]{2,3}県)(?=\S)", r"\1 ", t, count=1)  # 都道府県
    t = re.sub(r"([^\s\d]{1,5}?[区市])(?=[^\s\d])", r"\1 ", t, count=1)  # 千代田区丸の内 -> 千代田区 丸の内
    return re.sub(r"\s+", " ", t).strip()


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
    if "." in t:
        for rx, full in _IT_DOTTED:
            t = rx.sub(full, t)
    # 8 - 24 / 64 – 67 -> 8-24（哥伦比亚门牌、区间）；"1079 - 8º andar" 不合并（后面是楼层）
    t = re.sub(r"(?:(?<=\d)|(?<=\d[A-Z]))(?:\s*[–—]\s*|\s+-\s*|\s*-\s+)(?=\d+(?![\dA-Z]))|(?<=\d)\s*[–—]\s*(?=\d)",
               "-", t)
    t = re.sub(r"(?<=\d)(?=[A-Z]{3,})(?!(?:ST|ND|RD|TH|HS|BG|BV)\b)", " ", t)  # 500OXFORD -> 500 OXFORD
    t = re.sub(r"\b(SHOP|UNIT|LEVEL|SUITE|LOT|BLOCK|BLK|OFFICE)(?=\d)", r"\1 ", t)  # SHOP4068 -> SHOP 4068
    for m in _TOKEN.finditer(t):
        tok = m.group(0)
        if _THAI.match(tok):
            out.extend(_thai_tokenizer()(tok))
        elif tok == "#" or re.fullmatch(r"\d+(?:[/\-]\d+)*[A-Z]?|[A-Z]+", tok):
            out.append(tok)
        else:  # 字母数字混合且带连字符 / 斜杠：Karl-Marx -> KARL MARX；18/61、1/68F 保留
            # （71D-61 这类"门牌 + 字母 - 号"不拆：字母前面是数字时不在连字符处断开）
            out.extend(p for p in re.split(r"-(?=[A-Z])|(?<![0-9][A-Z])(?<=[A-Z])-|(?<=[A-Z])/(?=\d)|(?<=\d)/(?=[A-Z]{2})",
                                           tok) if p)
    return out


def expand(tokens: list[str], market: str) -> list[str]:
    lang = MARKET_LANG.get(market, "EN")
    table = ABBREV.get(lang, {})
    base = ABBREV["EN"] if lang in ("EN", "AR") or market in EN_BASE else {}
    out = []
    for t in _merge_initials(tokens):
        if lang == "DE" and len(t) > 4 and t.endswith("STR"):
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


def norm_postcode(pc: str | None, market: str = "") -> str:
    """邮编规范化：去空格、连字符和国家前缀（LT-01120 -> 01120、L-2348 -> 2348、〒104-0028 -> 1040028、
    01310-100 -> 01310100、SW1A 1AA -> SW1A1AA）；阿根廷 CPA（C1043AAZ）只取 4 位数字。"""
    if not pc:
        return ""
    s = re.sub(r"[\s\-〒]", "", fold(pc))
    m = re.fullmatch(r"[A-Z]{1,2}(\d{4,5})", s)
    if m and market not in ("GB", "IE", "CA", "NL"):
        s = m.group(1)
    if market == "AR":
        d = re.search(r"\d{4}", s)
        s = d.group(0) if d else s
    return s


_PC_FMT = {"CA": (r"^([A-Z]\d[A-Z])(\d[A-Z]\d)$", r"\1 \2"), "GB": (r"^(\w+?)(\d[A-Z]{2})$", r"\1 \2"),
           "IE": (r"^(\w{3})(\w{4})$", r"\1 \2"), "NL": (r"^(\d{4})([A-Z]{2})$", r"\1 \2"),
           "BR": (r"^(\d{5})(\d{3})$", r"\1-\2"), "PT": (r"^(\d{4})(\d{3})$", r"\1-\2"),
           "PL": (r"^(\d{2})(\d{3})$", r"\1-\2"), "CZ": (r"^(\d{3})(\d{2})$", r"\1 \2"),
           "SK": (r"^(\d{3})(\d{2})$", r"\1 \2"), "SE": (r"^(\d{3})(\d{2})$", r"\1 \2"),
           "JP": (r"^(\d{3})(\d{4})$", r"\1-\2"), "LT": (r"^(\d{5})$", r"LT-\1"), "LV": (r"^(\d{4})$", r"LV-\1"),
           "LU": (r"^(\d{4})$", r"L-\1")}


def fmt_postcode(pc: str | None, market: str) -> str:
    """规范化的邮编 -> 当地写法（M5V2K4 -> M5V 2K4、01310100 -> 01310-100、1000005 -> 100-0005）。"""
    if not pc:
        return ""
    rule = _PC_FMT.get(market)
    return re.sub(rule[0], rule[1], pc) if rule else pc


# 分级邮编的上一级（片区级）：完整邮编在参考库里查不到时用它印证道路（爱尔兰 Eircode 一户一码，D02 才是片区）
_PC_PREFIX = {"IE": 3, "CA": 3, "BR": 5, "PT": 4, "NL": 4, "SE": 3, "CZ": 3, "SK": 3}


def postcode_prefix(pc: str, market: str) -> str:
    if market == "GB":  # WC2H7AS -> WC2H7（邮区 + 小区数字）
        return pc[:-2] if len(pc) >= 5 else ""
    n = _PC_PREFIX.get(market)
    return pc[:n] if n and len(pc) > n else ""
