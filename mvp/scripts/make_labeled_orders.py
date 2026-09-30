"""生成"模拟真实订单"的标注数据：在还没有真实订单时，用来训练 / 评估置信度模型，并找出校验器的真实短板。

与 make_golden_set.py / make_noisy_set.py 的区别：
1. 按"下单渠道"模拟客户怎么填地址（网页表单 / App 邮编自动补全 / 聊天下单 / 电商平台导出 / 企业批量上传），
   每个渠道有自己的错误画像和比例（自然分布），而不是每类错误等量
2. 地址按下单人群抽样（组屋为主，其次公寓、写字楼、有地住宅），不是在参考库里均匀抽
3. 包含开放世界的情况：参考库里没有的新地址、马来西亚地址、中文地址、根本不是地址
4. 标签分两层：真实地址（相当于签收结果）+ 仅凭输入文字能判断到什么程度（可确定 / 有歧义 / 矛盾 / 误导 …）
5. 错拼模型、缩写表、单元号写法全部独立实现，不复用校验器的词典，避免"自己出题自己答"
6. "仅凭文字能判断到什么程度"由一个独立的标注规则（模拟拿着参考库查询的人工标注员）给出，
   只看客户实际写了哪些字段、写成了什么，不调用校验器

  python scripts/make_labeled_orders.py            # 默认 10,000 单 -> labeled/orders_sg_v1.csv
标注口径见 labeled/GUIDELINE.md，数据说明见 labeled/README.md。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import random
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp.reference import ReferenceDB  # noqa: E402

# ---------------------------------------------------------------------------------------------- 标签取值
RESOLVABLE, AMBIGUOUS, CONFLICTING, MISLEADING = "RESOLVABLE", "AMBIGUOUS", "CONFLICTING", "MISLEADING"
NOT_IN_REFERENCE, OUT_OF_REGION, NO_ADDRESS = "NOT_IN_REFERENCE", "OUT_OF_REGION", "NO_ADDRESS"
ACCEPT, CONFIRM, FIX, ADD_SUB = "ACCEPT", "CONFIRM", "FIX", "CONFIRM_ADD_SUBPREMISES"

# 需要改动地址本身的错误（校验器应提示确认）；其中"轻微"的两类直接通过也不算错
MAJOR_TAGS = {"STREET_TYPO", "STREET_NUMBER_WRONG", "STREET_TRUNCATED", "POSTAL_MISSING", "POSTAL_TYPO",
              "POSTAL_OTHER_ADDRESS", "BLOCK_MISSING", "BLOCK_TYPO", "BLOCK_LETTER_DROPPED", "BUILDING_ONLY",
              "CHINESE_ADDRESS", "BUILDING_TYPO"}
MINOR_TAGS = {"STREET_TYPO", "POSTAL_MISSING", "BUILDING_TYPO"}  # 楼宇名只是附加信息时，拼错不影响地址

# ---------------------------------------------------------------------------------------------- 分布假设
# 渠道占比与各渠道的错误画像都是假设（依据见 labeled/README.md），拿到真实订单后按真实比例重新加权即可
CHANNELS = {"web_form": 0.40, "mobile_app": 0.25, "chat": 0.15, "marketplace": 0.10, "b2b_upload": 0.10}
PTYPE_MIX = {
    "consumer": {"HDB": 0.66, "CONDO": 0.16, "LANDED": 0.08, "COMMERCIAL": 0.10},
    "b2b": {"COMMERCIAL": 0.80, "HDB": 0.10, "CONDO": 0.05, "LANDED": 0.05},
}
_BASE = dict(no_address=0.0, out_of_region=0.0, not_in_ref=0.0, chinese=0.0, building_only=0.0, unit_missing=0.0,
             street_typo=0.0, abbrev=0.0, town_abbrev=0.0, postal_missing=0.0, postal_typo=0.0, postal_other=0.0,
             leading_zero=0.0, block_missing=0.0, block_typo=0.0, letter_drop=0.0, street_number=0.0,
             location_hint=0.0, inline_noise=0.0, duplicate=0.0, truncate=0.0)
PROFILES = {
    # 网页结账表单：地址行 1 / 地址行 2 / 邮编分开填，最常见的问题是漏填单元号
    "web_form": {**_BASE, "no_address": 0.004, "out_of_region": 0.006, "not_in_ref": 0.02, "chinese": 0.002,
                 "building_only": 0.03, "unit_missing": 0.15, "street_typo": 0.05, "abbrev": 0.40,
                 "town_abbrev": 0.06, "postal_missing": 0.03, "postal_typo": 0.012, "postal_other": 0.004,
                 "block_missing": 0.01, "block_typo": 0.008, "letter_drop": 0.05, "street_number": 0.006,
                 "location_hint": 0.015, "inline_noise": 0.03, "duplicate": 0.02},
    # App：先填邮编、自动带出楼栋和道路，再手填单元号。邮编打错且恰好是另一个真实邮编时，会带出一整套"自洽但错误"的地址
    "mobile_app": {**_BASE, "no_address": 0.001, "out_of_region": 0.002, "not_in_ref": 0.02, "unit_missing": 0.07,
                   "postal_typo": 0.015, "postal_other": 0.004, "location_hint": 0.01,
                   "inline_noise": 0.01},
    # 聊天下单（WhatsApp / Telegram / 社媒私信）：自由文本，夹着姓名电话备注，缩写和漏写最多
    "chat": {**_BASE, "no_address": 0.03, "out_of_region": 0.01, "not_in_ref": 0.02, "chinese": 0.02,
             "building_only": 0.04, "unit_missing": 0.20, "street_typo": 0.10, "abbrev": 0.60, "town_abbrev": 0.20,
             "postal_missing": 0.20, "postal_typo": 0.015, "postal_other": 0.004, "block_missing": 0.03,
             "block_typo": 0.01, "letter_drop": 0.12, "street_number": 0.01, "location_hint": 0.03,
             "inline_noise": 1.0},
    # 电商平台导出：全大写、字段拼接、"SINGAPORE" 重复，偶尔被字段长度截断
    "marketplace": {**_BASE, "no_address": 0.002, "out_of_region": 0.004, "not_in_ref": 0.02, "building_only": 0.02,
                    "unit_missing": 0.12, "street_typo": 0.04, "abbrev": 0.30, "town_abbrev": 0.05,
                    "postal_missing": 0.01, "postal_typo": 0.01, "postal_other": 0.004, "leading_zero": 0.05,
                    "block_missing": 0.01, "block_typo": 0.006, "letter_drop": 0.05, "street_number": 0.005,
                    "location_hint": 0.01, "inline_noise": 0.08, "duplicate": 0.30, "truncate": 0.04},
    # 企业批量上传（商家 Excel）：写字楼为主，常只写楼宇名 + 单元号；Excel 吞掉邮编前导 0
    "b2b_upload": {**_BASE, "no_address": 0.003, "out_of_region": 0.01, "not_in_ref": 0.01, "building_only": 0.10,
                   "unit_missing": 0.10, "street_typo": 0.03, "abbrev": 0.30, "town_abbrev": 0.02,
                   "postal_missing": 0.03, "postal_typo": 0.01, "postal_other": 0.006, "leading_zero": 0.35,
                   "block_missing": 0.005, "block_typo": 0.005, "letter_drop": 0.03, "street_number": 0.004,
                   "inline_noise": 0.5},
}

# ---------------------------------------------------------------------------------------------- 写法素材（独立实现）
ABBR = {  # 全称 -> [(写法, 权重)]；包含一些校验器词典里没有的写法（Cent、S'goon、W'lands …），真实订单里就有
    "AVENUE": [("Ave", 8), ("Ave.", 2), ("Av", 1)], "STREET": [("St", 8), ("St.", 2), ("Str", 1)],
    "ROAD": [("Rd", 8), ("Rd.", 2)], "DRIVE": [("Dr", 6), ("Drv", 1)], "CRESCENT": [("Cres", 6), ("Cresc", 1)],
    "CLOSE": [("Cl", 1)], "LANE": [("Ln", 1)], "CENTRAL": [("Ctrl", 5), ("Cent", 1)],
    "NORTH": [("Nth", 6), ("N", 1)], "SOUTH": [("Sth", 6)], "UPPER": [("Upp", 4), ("Upr", 1)],
    "JALAN": [("Jln", 8), ("Jl", 1)], "LORONG": [("Lor", 8), ("Lrg", 1)], "BUKIT": [("Bt", 6), ("Bkt", 3)],
    "KAMPONG": [("Kg", 4), ("Kpg", 1)], "TANJONG": [("Tg", 3), ("Tanjung", 1)], "TERRACE": [("Terr", 1)],
    "PLACE": [("Pl", 1)], "PARK": [("Pk", 1)], "HEIGHTS": [("Hts", 1)], "GARDENS": [("Gdns", 1)],
    "INDUSTRIAL": [("Ind", 3), ("Indus", 1)], "MOUNT": [("Mt", 2)], "BOULEVARD": [("Blvd", 2)],
    "EAST": [("E", 1)], "WEST": [("W", 1)],
}
TOWN_ABBR = {
    "ANG MO KIO": [("AMK", 10)], "CHOA CHU KANG": [("CCK", 8)], "TOA PAYOH": [("TPY", 3)],
    "JURONG WEST": [("JW", 3), ("Jurong W", 2)], "BUKIT BATOK": [("BB", 2), ("Bt Batok", 5)],
    "BUKIT PANJANG": [("BP", 2), ("Bt Panjang", 4)], "BUKIT MERAH": [("Bt Merah", 5)],
    "BUKIT TIMAH": [("Bt Timah", 5)], "PASIR RIS": [("PR", 1)], "SENGKANG": [("Seng Kang", 3), ("SK", 1)],
    "PUNGGOL": [("PG", 1)], "TAMPINES": [("Tamp", 2), ("TPN", 1)], "WOODLANDS": [("WDL", 2), ("W'lands", 2)],
    "YISHUN": [("YS", 1)], "HOUGANG": [("HG", 1)], "SERANGOON": [("S'goon", 2), ("SRG", 1)],
    "SEMBAWANG": [("SBW", 1)], "COMMONWEALTH": [("C'wealth", 3)],
}
KEYBOARD = {"Q": "WA", "W": "QESA", "E": "WRDS", "R": "ETFD", "T": "RYGF", "Y": "TUHG", "U": "YIJH", "I": "UOKJ",
            "O": "IPLK", "P": "OL", "A": "QWSZ", "S": "AWEDXZ", "D": "SERFCX", "F": "DRTGVC", "G": "FTYHBV",
            "H": "GYUJNB", "J": "HUIKMN", "K": "JIOLM", "L": "KOP", "Z": "ASX", "X": "ZSDC", "C": "XDFV",
            "V": "CFGB", "B": "VGHN", "N": "BHJM", "M": "NJK"}
NUMPAD = {"0": "12", "1": "240", "2": "1350", "3": "26", "4": "1578", "5": "2468", "6": "3598", "7": "48",
          "8": "5796", "9": "68"}
COMMON_MISSPELL = {  # 本地常见的听写 / 习惯性错拼
    "CRESCENT": ["CRESENT", "CRESCANT"], "AVENUE": ["AVENU", "AVENEU"], "BOULEVARD": ["BOULEVARDE"],
    "TERRACE": ["TERACE"], "INDUSTRIAL": ["INDUSTRAIL"], "SERANGOON": ["SARANGOON", "SERANGGON"],
    "HOUGANG": ["HOUGAN", "HOGANG"], "PUNGGOL": ["PUNGOL", "PONGGOL"], "YISHUN": ["YISUN", "YISHUNG"],
    "JURONG": ["JURUNG"], "CHOA CHU KANG": ["CHUA CHU KANG", "CHOA CHUKANG"], "TAMPINES": ["TEMPINES", "TAMPINESE"],
    "BEDOK": ["BEDOC"], "WOODLANDS": ["WOODLAND", "WOODLANS"], "SEMBAWANG": ["SEMBAWAN"],
    "CLEMENTI": ["CLEMENTY", "CLEMENTE"], "PASIR RIS": ["PASIRRIS", "PASIR RISE"], "TOA PAYOH": ["TOA PAYO", "TOAPAYOH"],
    "ANG MO KIO": ["ANGMOKIO", "ANG MOH KIO"], "SENGKANG": ["SENKANG", "SENGKAN"], "GEYLANG": ["GAYLANG"],
    "BISHAN": ["BISAN"], "COMPASSVALE": ["COMPASVALE", "COMPASS VALE"], "EUNOS": ["EUNUS"],
}
CN_TOWN = {"ANG MO KIO": "宏茂桥", "TAMPINES": "淡滨尼", "JURONG WEST": "裕廊西", "JURONG EAST": "裕廊东",
           "SENGKANG": "盛港", "PUNGGOL": "榜鹅", "WOODLANDS": "兀兰", "YISHUN": "义顺", "HOUGANG": "后港",
           "TOA PAYOH": "大巴窑", "BISHAN": "碧山", "BEDOK NORTH": "勿洛北", "BEDOK SOUTH": "勿洛南", "BEDOK": "勿洛",
           "PASIR RIS": "巴西立", "CHOA CHU KANG": "蔡厝港", "BUKIT PANJANG": "武吉班让", "BUKIT BATOK": "武吉巴督",
           "CLEMENTI": "金文泰", "BUKIT MERAH": "红山", "SERANGOON": "实龙岗", "SEMBAWANG": "三巴旺", "GEYLANG": "芽笼"}
CN_TYPE = {"AVENUE": "道", "STREET": "街", "DRIVE": "通道", "ROAD": "路", "CENTRAL": "中"}

NAMES = ["Tan Wei Ming", "Nurul Huda", "Lim Jia Hui", "Suresh Pillai", "Ong Bee Leng", "Mohd Irfan", "Chloe Tan",
         "Ravi Shankar", "Koh Seng Huat", "Siti Rahmah", "Marcus Lee", "Yeo Hui Min", "Arjun Nair", "Grace Chua",
         "Farhan Ismail", "Wendy Lau", "Benjamin Ho", "Aishah Rahman", "Joel Sim", "Priscilla Goh"]
COMPANIES = ["Northstar Analytics Pte Ltd", "Harbourfront Trading Pte. Ltd.", "Kian Hock Engineering Pte Ltd",
             "Lumen Health Pte Ltd", "Brightpath Education Pte Ltd", "Orchid Logistics Pte Ltd",
             "Tembusu Capital LLP", "Redhill Foods Pte. Ltd.", "Meridian Legal LLC", "Suntory Supplies Pte Ltd"]
NOTES = ["pls call when reach", "leave at door pls", "no need call", "deliver after 7pm", "can pass to guard",
         "fragile!!", "cash on delivery", "don't ring bell baby sleeping", "sat only", "call b4 come",
         "放门口就好", "到了打给我", "谢谢", "put at letterbox", "if no one home leave at neighbour"]
LOCATION_HINTS = ["void deck", "lift lobby B", "guardhouse", "near the lift", "at the carpark", "letter box",
                  "side gate", "main lobby"]
NO_ADDRESS_TEXTS = ["self collect", "Self pick up at Tampines outlet", "will collect myself", "same as previous order",
                    "pls check with me", "N/A", "0", "Singapore", "home", "to be advised", "deliver to my office",
                    "whatsapp me for address", "?", "test", "asdf", "Tampines", "near Jurong East MRT",
                    "collect at Paya Lebar Quarter", "same address", "pls call"]
MY_NAMES = ["Setia", "Bukit Indah", "Molek", "Perling", "Mutiara", "Pelangi", "Sutera", "Impian Emas", "Tebrau",
            "Nusa Bestari", "Universiti", "Daya", "Mount Austin", "Sri Skudai"]
MY_CITIES = [("Johor Bahru", "80"), ("Skudai", "81"), ("Iskandar Puteri", "79"), ("Kulai", "81"),
             ("Pasir Gudang", "81"), ("Masai", "81")]
NEW_ESTATES = {"Tengah": "69", "Bidadari": "36", "Keat Hong": "68", "Tampines North": "52", "Northshore": "82",
               "Mount Pleasant": "29", "Brickland": "69", "Plantation": "69", "Kranji Green": "73",
               "Chencharu": "76", "Lentor": "78", "Tanjong Rhu Vista": "43"}  # 片区 -> 邮区（邮编前两位）
NEW_KINDS = ["", "Garden", "Park", "Forest", "Grove"]
NEW_TYPES = ["Walk", "Drive", "Crescent", "Avenue", "Link", "Way", "Lane", "Rise"]
NEW_CONDOS = ["The Arden", "Lentor Mansion", "Tembusu Grand", "Parc Clematis Vista", "Hillhaven Residences",
              "The Continuum Edge", "Pinetree Hill Suites", "Grand Dunman Park", "Sceneca Bay", "Florence Crest"]

# 楼宇名关键词：判断物业类型（启发式，见 README）
COMM_WORDS = ("TOWER", "CENTRE", "CENTER", "PLAZA", "BUILDING", "MALL", "SQUARE", "HUB", "INDUSTRIAL", "TECHPARK",
              "BUSINESS", "COMPLEX", "EXCHANGE", "FACTORY", "WAREHOUSE", "LOGISTICS", "HOTEL", "OFFICE", "SHOPPING")
RESI_WORDS = ("RESIDENCE", "CONDO", "SUITES", "COURT", "APARTMENT", "MANSION", "VILLE", "RESIDENCY", "REGENCY",
              "LOFT", "@", "HEIGHTS", "VIEW", "PARC", "VISTA", "LODGE")
AREA_WORDS = ("ESTATE", "CONSERVATION AREA", "GARDEN", "PARK")
# 不会有人往这里下单的楼宇名（工地、设施）
SKIP_WORDS = ("TEMPORARY", "SITE OFFICE", "SUBSTATION", "CARPARK", "CAR PARK", "PUMP", "BIN CENTRE", "MRT",
              "BUS INTERCHANGE", "BUS DEPOT", "CONSTRUCTION")

HDB_BLK = re.compile(r"(\d{1,3})([A-H]?)")


def digits(s: str) -> str:
    return "".join(c for c in s if c.isdigit())


def is_hdb(e) -> bool:
    """新加坡组屋邮编 = 2 位邮区 + 1 位字母后缀编码（A=1…）+ 3 位楼号，例如 Blk 655C -> 823655。"""
    m = HDB_BLK.fullmatch(e.blk)
    if not m:
        return False
    d, letter = m.groups()
    return e.postal[3:] == d.zfill(3) and e.postal[2] == ("0" if not letter else str(ord(letter) - 64))


def weighted(rng: random.Random, pairs):
    items = list(pairs.items()) if isinstance(pairs, dict) else list(pairs)
    x = rng.random() * sum(w for _, w in items)
    for item, w in items:
        x -= w
        if x <= 0:
            return item
    return items[-1][0]


def title(s: str) -> str:
    return " ".join(w if any(c.isdigit() for c in w) else w[:1].upper() + w[1:].lower() for w in s.split())


# ---------------------------------------------------------------------------------------------- 参考库视图
class World:
    """参考库 + 标注员视角的查询（独立于校验器：不用它的规范键、解析器和召回逻辑）。"""

    def __init__(self, db: ReferenceDB):
        self.db = db
        self.road_key = {e.road: e.road_key for e in db.entities}  # 原始道路名 -> 参考库道路键
        self.roads_by_digits: dict[tuple[str, ...], list[str]] = defaultdict(list)
        for name in sorted(self.road_key):
            self.roads_by_digits[tuple(re.findall(r"\d+", name))].append(name)
        self.building_ids: dict[str, set[int]] = defaultdict(set)
        for e in db.entities:
            for b in e.buildings:
                self.building_ids[b.upper()].add(e.eid)
        self.building_names = sorted(self.building_ids)
        self.ptype = [self._classify(e) for e in db.entities]
        self.by_type: dict[str, list[int]] = defaultdict(list)
        for e in db.entities:
            self.by_type[self.ptype[e.eid]].append(e.eid)
        self.hdb_roads = sorted({db.entities[i].road for i in self.by_type["HDB"]})
        self.postals = set(db.by_postal)
        # 同一个地址在参考库里可能有两条记录（如 SAINT JOHN'S ISLAND 与 ST. JOHN'S ISLAND），按"楼栋 + 道路 + 邮编"视为同一地址
        self.addr = [(e.blk, e.road_key, e.postal) for e in db.entities]

    @staticmethod
    def _classify(e) -> str:
        if is_hdb(e):
            return "HDB"
        names = [b for b in e.buildings if not any(w in b for w in AREA_WORDS + SKIP_WORDS)]
        if any(any(w in b for w in COMM_WORDS) for b in names):
            return "COMMERCIAL"
        if any(any(w in b for w in RESI_WORDS) or b.startswith("THE ") for b in names):
            return "CONDO"
        return "LANDED"

    def building_name(self, e) -> str | None:
        """客户会写的楼宇名：公寓 / 写字楼名，不用片区名和 HDB-XXX 这类内部名。"""
        words = COMM_WORDS if self.ptype[e.eid] == "COMMERCIAL" else RESI_WORDS
        good = [b for b in e.buildings if not b.startswith("HDB") and not any(w in b for w in AREA_WORDS + SKIP_WORDS)]
        typed = [b for b in good if any(w in b for w in words) or b.startswith("THE ")]
        return (typed or good or [None])[0]

    # ---- 标注员能不能认出客户写的东西
    def recognize_road(self, written: str | None) -> str | None:
        if not written:
            return None
        if written in self.road_key:
            return self.road_key[written]
        pool = self.roads_by_digits.get(tuple(re.findall(r"\d+", written)), [])
        hits = process.extract(written, pool, scorer=fuzz.ratio, limit=2)
        if not hits or hits[0][1] < 85 or (len(hits) > 1 and hits[1][1] > hits[0][1] - 4):
            return None  # 认不出，或像两条路：人也判断不了
        return self.road_key[hits[0][0]]

    def recognize_building(self, written: str | None) -> set[int]:
        if not written:
            return set()
        if written in self.building_ids:
            return set(self.building_ids[written])
        hits = process.extract(written, self.building_names, scorer=fuzz.ratio, limit=2)
        if not hits or hits[0][1] < 90 or (len(hits) > 1 and hits[1][1] > hits[0][1] - 4):
            return set()
        return set(self.building_ids[hits[0][0]])


@dataclass
class Written:
    """客户实际写下的地址字段（道路为全称，缩写 / 大小写等无害变化在渲染时才加）。"""
    blk: str | None
    road: str | None
    postal: str | None
    building: str | None = None
    unit: tuple[str, str] | None = None
    states: dict = field(default_factory=dict)


def resolve(world: World, w: Written) -> tuple[str, int | None, str]:
    """标注规则：仅凭客户写下的字段 + 参考库，能否唯一确定一个地址。返回（判断, 地址实体, 说明）。

    1. 每个认得出的字段给出一组候选：邮编 -> 该邮编下的地址；楼栋 + 道路 -> 该地址（楼栋号只差字母后缀且唯一时视为同一栋）；
       只有道路 -> 整条路；楼宇名 -> 该楼宇
    2. 各组取交集：恰好 1 个 -> 可确定；多个 -> 有歧义；空 -> 字段互相矛盾
    3. 矛盾时按"支持字段数"裁决：某个候选得到 >= 2 个字段支持且严格多于其他候选 -> 可确定（需纠错），否则 -> 矛盾
    """
    db = world.db
    road = world.recognize_road(w.road)
    postal = w.postal if w.postal in world.postals else None
    bids = world.recognize_building(w.building)
    sets: list[tuple[str, set[int]]] = []
    if postal:
        p_ids = set(db.by_postal[postal])
        if w.blk and not road:
            narrowed = {i for i in p_ids if db.entities[i].blk == w.blk}
            p_ids = narrowed or p_ids
        sets.append(("邮编", p_ids))
    if road:
        on_road = set(db.by_road[road])
        if w.blk:
            br = set(db.by_blk_road.get((w.blk, road), []))
            if not br:
                var = {i for i in on_road if digits(db.entities[i].blk) == digits(w.blk)}
                br = var if len(var) == 1 else set()
            sets.append(("楼栋+道路", br) if br else ("道路", on_road))
        else:
            sets.append(("道路", on_road))
    if bids:
        sets.append(("楼宇名", bids))
    if not sets:
        return NO_ADDRESS, None, "没有认得出的地址字段"
    inter = set.intersection(*[s for _, s in sets])
    used = "+".join(n for n, _ in sets)
    addrs = {world.addr[i] for i in inter}
    if len(addrs) == 1:
        return RESOLVABLE, min(inter), f"{used} 唯一确定"
    if len(addrs) > 1:
        return AMBIGUOUS, None, f"{used} 对应 {len(addrs)} 个地址"

    pool = set().union(*[s for _, s in sets if len(s) <= 300])

    def support(i: int) -> float:
        e = db.entities[i]
        s = float(postal == e.postal) + float(road == e.road_key) + float(i in bids)
        if w.blk:
            s += 1.0 if e.blk == w.blk else 0.5 if digits(e.blk) == digits(w.blk) else 0.0
        return s

    best: dict[tuple, tuple[float, int]] = {}
    for i in pool:
        best[world.addr[i]] = max(best.get(world.addr[i], (0.0, i)), (support(i), i))
    ranked = sorted(best.values(), reverse=True)
    if ranked and ranked[0][0] >= 2 and (len(ranked) == 1 or ranked[0][0] > ranked[1][0]):
        return RESOLVABLE, ranked[0][1], f"{used} 矛盾，按多数字段裁决"
    return CONFLICTING, None, f"{used} 互相矛盾，无法判断哪个字段错了"


# ---------------------------------------------------------------------------------------------- 错误注入
def misspell_word(word: str, rng: random.Random) -> str:
    letters = [i for i, c in enumerate(word) if c.isalpha()]
    if len(letters) < 4:
        return word
    i = rng.choice(letters[1:])  # 首字母很少打错
    op = weighted(rng, {"keyboard": 30, "delete": 20, "double": 10, "undouble": 10, "swap": 15, "vowel": 15})
    if op == "undouble":
        dbl = [j for j in range(1, len(word)) if word[j] == word[j - 1] and word[j].isalpha()]
        if dbl:
            j = rng.choice(dbl)
            return word[:j] + word[j + 1:]
        op = "delete"
    if op == "keyboard" and word[i] in KEYBOARD:
        return word[:i] + rng.choice(KEYBOARD[word[i]]) + word[i + 1:]
    if op == "double":
        return word[:i] + word[i] + word[i:]
    if op == "swap" and i + 1 < len(word) and word[i + 1].isalpha() and word[i + 1] != word[i]:
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    if op == "vowel" and word[i] in "AEIOU":
        return word[:i] + rng.choice([v for v in "AEIOU" if v != word[i]]) + word[i + 1:]
    return word[:i] + word[i + 1:]


def misspell_road(road: str, rng: random.Random) -> str:
    phrases = [p for p in COMMON_MISSPELL if f" {p} " in f" {road} "]
    if phrases and rng.random() < 0.5:
        p = rng.choice(phrases)
        return f" {road} ".replace(f" {p} ", f" {rng.choice(COMMON_MISSPELL[p])} ", 1).strip()
    words = road.split()
    idx = [i for i, t in enumerate(words) if t.isalpha() and len(t) >= 4]
    if not idx:
        return road
    names = [i for i in idx if words[i] not in ABBR]
    i = rng.choice(names) if names and rng.random() < 0.75 else rng.choice(idx)
    words[i] = misspell_word(words[i], rng)
    return " ".join(words)


def wrong_street_number(road: str, rng: random.Random) -> str | None:
    m = re.fullmatch(r"(.*\D)(\d+)", road)
    if not m:
        return None
    head, n = m.group(1), m.group(2)
    if rng.random() < 0.3:
        for a, b in (("AVENUE", "STREET"), ("STREET", "AVENUE")):
            if f" {a} " in f" {head}":
                return head.replace(a, b) + n
    options = {str(int(n) + 1), str(max(int(n) - 1, 1)), n[::-1] if len(n) > 1 else n, n[:-1] if len(n) > 1 else n}
    options.discard(n)
    options.discard("")
    return head + rng.choice(sorted(options)) if options else None


def typo_postal(p: str, rng: random.Random) -> str:
    if rng.random() < 0.6:
        i = rng.randrange(len(p) - 1)
        if p[i] != p[i + 1]:
            return p[:i] + p[i + 1] + p[i] + p[i + 2:]
    i = rng.randrange(len(p))
    return p[:i] + rng.choice(NUMPAD[p[i]]) + p[i + 1:]


def typo_block(blk: str, rng: random.Random) -> str:
    d, rest = digits(blk), blk[len(digits(blk)):]
    if len(d) >= 2 and rng.random() < 0.5:
        i = rng.randrange(len(d) - 1)
        d2 = d[:i] + d[i + 1] + d[i] + d[i + 2:]
    else:
        i = rng.randrange(len(d))
        d2 = d[:i] + rng.choice(NUMPAD[d[i]]) + d[i + 1:]
    d2 = d2.lstrip("0") or "1"
    return d2 + rest


def make_unit(ptype: str, rng: random.Random) -> tuple[str, str] | None:
    if ptype == "HDB":
        floor = int(min(max(rng.gauss(8, 5), 2), 40))
        no = rng.randint(1, 350) if rng.random() < 0.9 else rng.randint(1000, 1999)
    elif ptype == "CONDO":
        floor, no = int(min(1 + rng.expovariate(1 / 7), 36)), rng.randint(1, 12)
    elif ptype == "COMMERCIAL":
        if rng.random() < 0.15:
            return (rng.choice(["B1", "B1", "B2"]), f"{rng.randint(1, 80):02d}")
        floor, no = int(min(1 + rng.expovariate(1 / 6), 45)), rng.randint(1, 20)
    else:
        return None
    return (f"{floor:02d}", f"{no:02d}")


def std_unit(u: tuple[str, str] | None) -> str:
    return f"#{u[0]}-{u[1]}" if u else ""


def fmt_unit(u: tuple[str, str], rng: random.Random, typed: bool = True) -> str:
    f, n = u
    if not typed:
        return f"#{f}-{n}"
    fl = f if f.startswith("B") else str(int(f))
    options = [(f"#{f}-{n}", 50), (f"# {f}-{n}", 5), (f"#{fl}-{n}", 8), (f"{f}-{n}", 12), (f"Unit {f}-{n}", 6),
               (f"unit #{f}-{n}", 4), (f"#{f} - {n}", 4)]
    if not f.startswith("B"):
        options.append((f"Level {fl} Unit {n}", 3))
    return weighted(rng, options)


# ---------------------------------------------------------------------------------------------- 渲染
def render_road(road: str, rng: random.Random, abbrev_p: float, town_p: float, tags: list[str]) -> str:
    """道路全称 -> 客户写法（先转成首字母大写，再替换成缩写；缩写保留自身大小写，如 AMK）。"""
    out = title(road)
    if rng.random() < town_p:
        for full, alts in TOWN_ABBR.items():
            if f" {title(full)} " in f" {out} ":
                out = f" {out} ".replace(f" {title(full)} ", f" {weighted(rng, alts)} ", 1).strip()
                tags.append("TOWN_ABBREV")
                break
    if rng.random() < abbrev_p:
        words = out.split()
        changed = False
        for i, t in enumerate(words):
            if t.upper() in ABBR and t == title(t) and rng.random() < 0.8:
                words[i] = weighted(rng, ABBR[t.upper()])
                changed = True
        if changed:
            tags.append("ABBREV")
        out = " ".join(words)
    return out


def case_style(text: str, rng: random.Random, weights: dict) -> str:
    style = weighted(rng, weights)
    if style == "lower":
        return text.lower()
    if style == "upper":
        return text.upper()
    if style == "mixed":
        return "".join(c.upper() if rng.random() < 0.3 else c.lower() for c in text)
    return text


def postal_text(p: str, rng: random.Random, weights: dict) -> str:
    fmt = weighted(rng, weights)
    return fmt.format(p=p)


def phone(rng: random.Random) -> str:
    n = f"{rng.choice('89')}{rng.randint(0, 9999999):07d}"
    return weighted(rng, {f"{n[:4]} {n[4:]}": 4, n: 4, f"+65 {n[:4]} {n[4:]}": 3, f"+65{n}": 1, f"(+65) {n}": 1})


def blk_prefix(ptype: str, rng: random.Random) -> str:
    if ptype == "HDB":
        return weighted(rng, {"Blk ": 45, "": 35, "Block ": 8, "BLK": 4, "Blk. ": 4, "blk ": 4})
    if ptype == "LANDED":
        return weighted(rng, {"": 85, "No. ": 10, "No ": 5})
    return ""


# ---------------------------------------------------------------------------------------------- 生成
class Generator:
    def __init__(self, world: World, seed: int):
        self.w = world
        self.rng = random.Random(seed)

    # ---- 场景：参考库里的真实地址
    def regular(self, channel: str, prof: dict) -> dict:
        rng, db, world = self.rng, self.w.db, self.w
        mix = PTYPE_MIX["b2b" if channel == "b2b_upload" else "consumer"]
        ptype = weighted(rng, mix)
        e = db.entities[rng.choice(world.by_type[ptype])]
        truth_unit = make_unit(ptype, rng)
        bname = world.building_name(e) if ptype in ("CONDO", "COMMERCIAL") else None
        w = Written(blk=e.blk, road=e.road, postal=e.postal, unit=truth_unit)
        tags: list[str] = []
        st = {"blk": "ok", "street": "ok", "postal": "ok", "building": "absent", "unit": "ok" if truth_unit else "n/a"}

        chinese = rng.random() < prof["chinese"] and ptype == "HDB" and self._cn_road(e.road)
        if chinese:
            tags.append("CHINESE_ADDRESS")
        elif bname and rng.random() < prof["building_only"]:
            w.blk = w.road = None
            w.building = bname
            st.update(blk="missing", street="missing", building="ok")
            tags.append("BUILDING_ONLY")
            if rng.random() < 0.6:
                w.postal = None
                st["postal"] = "missing"
                tags.append("POSTAL_MISSING")
        elif bname and rng.random() < (0.5 if ptype == "COMMERCIAL" else 0.3):
            w.building = bname
            st["building"] = "ok"
        if w.building and rng.random() < prof["street_typo"]:
            typo = misspell_word(w.building, rng)
            if typo != w.building:
                w.building = typo
                st["building"] = "typo"
                tags.append("BUILDING_TYPO")

        if truth_unit and rng.random() < prof["unit_missing"]:
            w.unit = None
            st["unit"] = "missing"
            tags.append("UNIT_MISSING")

        if w.road and not chinese:
            if rng.random() < prof["street_typo"]:
                bad = misspell_road(w.road, rng)
                if bad != w.road:
                    w.road = bad
                    st["street"] = "typo"
                    tags.append("STREET_TYPO")
            elif rng.random() < prof["street_number"]:
                bad = wrong_street_number(w.road, rng)
                if bad and bad != w.road:
                    w.road = bad
                    st["street"] = "wrong_number"
                    tags.append("STREET_NUMBER_WRONG")

        if chinese:
            if rng.random() < 0.5:
                w.postal = None
                st["postal"] = "missing"
                tags.append("POSTAL_MISSING")
        elif w.postal:
            r = rng.random()
            if r < prof["postal_missing"]:
                w.postal = None
                st["postal"] = "missing"
                tags.append("POSTAL_MISSING")
            elif r < prof["postal_missing"] + prof["postal_typo"]:
                w.postal = typo_postal(e.postal, rng)
                st["postal"] = "typo_valid" if w.postal in world.postals else "typo_invalid"
                tags.append("POSTAL_TYPO")
            elif r < prof["postal_missing"] + prof["postal_typo"] + prof["postal_other"]:
                same = [i for i in db.by_postal if i[:2] == e.postal[:2] and i != e.postal]
                w.postal = rng.choice(same) if same and rng.random() < 0.6 else db.entities[
                    rng.randrange(len(db.entities))].postal
                st["postal"] = "other_address"
                tags.append("POSTAL_OTHER_ADDRESS")

        if channel == "mobile_app" and (st["postal"] == "typo_valid" or st["postal"] == "other_address"):
            # App 按打错的邮编自动带出另一个真实地址，客户没发现：整套字段自洽但指向错误地址
            x = db.entities[db.by_postal[w.postal][0]]
            w.blk, w.road = x.blk, x.road
            st.update(blk="autofilled_wrong", street="autofilled_wrong")
            tags.append("AUTOFILL_WRONG")
        elif w.blk and not chinese:
            if rng.random() < prof["block_missing"] and w.postal:
                w.blk = None
                st["blk"] = "missing"
                tags.append("BLOCK_MISSING")
            elif rng.random() < prof["block_typo"]:
                w.blk = typo_block(e.blk, rng)
                st["blk"] = "typo"
                tags.append("BLOCK_TYPO")
            elif e.blk[-1:].isalpha() and rng.random() < prof["letter_drop"]:
                w.blk = digits(e.blk)
                st["blk"] = "letter_dropped"
                tags.append("BLOCK_LETTER_DROPPED")

        w.states = st
        text, fields = self.render(channel, prof, w, ptype, tags, chinese=chinese)
        label, rid, why = resolve(world, w)
        if label == RESOLVABLE and world.addr[rid] != world.addr[e.eid]:
            x = db.entities[rid]
            label, why = MISLEADING, f"{why}；但指向 {x.blk} {x.road} {x.postal}，不是客户的真实地址"
        if chinese:
            label, why = RESOLVABLE, "中文地址：懂中文的标注员可按市镇 / 道路 / 座号确定"
        return self.row(channel, fields, text, e, ptype, truth_unit, label, why, tags, st)

    def _cn_road(self, road: str) -> str | None:
        for town, cn in sorted(CN_TOWN.items(), key=lambda kv: -len(kv[0])):
            m = re.fullmatch(rf"{town} (AVENUE|STREET|DRIVE|ROAD|CENTRAL)(?: (\d+))?", road)
            if m:
                return f"{cn}{m.group(2) or ''}{CN_TYPE[m.group(1)]}"
        return None

    # ---- 场景：参考库里没有的新地址（新组屋 / 新片区 / 新公寓）
    def not_in_reference(self, channel: str, prof: dict) -> dict:
        rng, db, world = self.rng, self.w.db, self.w
        kind = weighted(rng, {"new_hdb_block": 55, "new_estate": 25, "new_condo": 20})
        for _ in range(200):
            if kind == "new_hdb_block":
                road = rng.choice(world.hdb_roads)
                ids = [i for i in db.by_road[world.road_key[road]] if world.ptype[i] == "HDB"]
                base = db.entities[rng.choice(ids)]
                n = int(digits(base.blk))
                if rng.random() < 0.6:
                    letter = rng.choice("ABCD")
                    blk = f"{n}{letter}"
                    postal = base.postal[:2] + str(ord(letter) - 64) + str(n % 1000).zfill(3)
                else:
                    n2 = n + rng.choice([-7, -3, 2, 5, 11, 14])
                    if n2 <= 0 or n2 >= 1000:
                        continue
                    blk, postal = str(n2), base.postal[:2] + "0" + str(n2).zfill(3)
                if (blk, world.road_key[road]) in db.by_blk_road or postal in world.postals:
                    continue
                ptype, bname = "HDB", None
            elif kind == "new_estate":
                estate, kind_w, typ = rng.choice(sorted(NEW_ESTATES)), rng.choice(NEW_KINDS), rng.choice(NEW_TYPES)
                road = " ".join(x for x in (estate, kind_w, typ) if x).upper()
                if rng.random() < 0.4:
                    road += f" {rng.randint(1, 9)}"
                if road in world.road_key or world.recognize_road(road):
                    continue
                sector = NEW_ESTATES[estate]
                n = rng.randint(100, 999)
                letter = rng.choice(["", "", "A", "B", "C"])
                blk = f"{n}{letter}"
                postal = sector + ("0" if not letter else str(ord(letter) - 64)) + str(n).zfill(3)
                if postal in world.postals:
                    continue
                ptype, bname = "HDB", None
            else:
                base = db.entities[rng.choice(world.by_type["CONDO"] + world.by_type["LANDED"])]
                road, blk = base.road, str(rng.randint(1, 120))
                bname = rng.choice(NEW_CONDOS).upper()
                postal = base.postal[:3] + f"{rng.randint(0, 999):03d}"
                if (blk, base.road_key) in db.by_blk_road or postal in world.postals or bname in world.building_ids:
                    continue
                ptype = "CONDO"
            break
        else:
            raise RuntimeError("找不到参考库之外的新地址，检查参考库")
        truth_unit = make_unit(ptype, rng)
        w = Written(blk=blk, road=road, postal=postal, building=bname if bname and rng.random() < 0.6 else None,
                    unit=truth_unit)
        tags = [kind.upper()]
        st = {"blk": "ok", "street": "ok", "postal": "ok", "building": "ok" if w.building else "absent",
              "unit": "ok" if truth_unit else "n/a"}
        if rng.random() < prof["unit_missing"]:
            w.unit = None
            st["unit"] = "missing"
            tags.append("UNIT_MISSING")
        if rng.random() < prof["postal_missing"]:
            w.postal = None
            st["postal"] = "missing"
            tags.append("POSTAL_MISSING")
        w.states = st
        text, fields = self.render(channel, prof, w, ptype, tags)
        _, rid, why = resolve(world, w)
        why = "参考库（2017 年数据）里没有这个地址" + (
            f"；文字恰好能对上参考库里的 {db.entities[rid].blk} {db.entities[rid].road}" if rid is not None else "")
        truth = {"blk": blk, "road": road, "postal": postal, "building": bname or ""}
        return self.row(channel, fields, text, None, ptype, truth_unit, NOT_IN_REFERENCE, why, tags, st, truth=truth)

    # ---- 场景：马来西亚地址 / 根本不是地址
    def out_of_region(self, channel: str, prof: dict) -> dict:
        rng = self.rng
        city, pre = rng.choice(MY_CITIES)
        taman = rng.choice(MY_NAMES)
        pc = pre + f"{rng.randint(0, 999):03d}"
        a1 = weighted(rng, {f"No. {rng.randint(1, 80)}, Jalan {taman} {rng.randint(1, 12)}/{rng.randint(1, 9)}": 5,
                            f"{rng.randint(1, 80)} Jln {taman} {rng.randint(1, 30)}": 3,
                            f"Unit {rng.randint(1, 30)}-{rng.randint(1, 12)}, Menara {taman}": 1})
        a2 = f"Taman {taman}"
        text = f"{a1}, {a2}, {pc} {city}, Johor" + (", Malaysia" if rng.random() < 0.5 else "")
        text = case_style(text, rng, {"as_is": 6, "lower": 2, "upper": 2})
        fields = {"address_line1": text, "address_line2": "", "postal_field": ""}
        return self.row(channel, fields, text, None, "", None, OUT_OF_REGION, "马来西亚（柔佛）地址", ["OUT_OF_REGION"],
                        {}, truth={"blk": "", "road": "", "postal": pc, "building": ""})

    def no_address(self, channel: str, prof: dict) -> dict:
        rng = self.rng
        text = rng.choice(NO_ADDRESS_TEXTS)
        if channel == "chat" and rng.random() < 0.6:
            text = f"{rng.choice(NAMES)} {phone(rng)}\n{text}"
        fields = {"address_line1": text, "address_line2": "", "postal_field": ""}
        return self.row(channel, fields, text, None, "", None, NO_ADDRESS, "没有可投递的地址", ["NO_ADDRESS"], {})

    # ---- 按渠道渲染成客户实际提交的文字
    def render(self, channel: str, prof: dict, w: Written, ptype: str, tags: list[str],
               chinese: bool = False) -> tuple[str, dict]:
        rng = self.rng
        typed = channel != "mobile_app"
        unit = fmt_unit(w.unit, rng, typed) if w.unit else ""
        if unit and unit != std_unit(w.unit):
            tags.append("UNIT_FORMAT")
        if chinese:
            cn = self._cn_road(w.road)
            core = weighted(rng, {f"{cn}{w.blk}座": 5, f"Blk {w.blk} {cn}": 2, f"{cn} {w.blk}座": 2})
            street_part = core
        elif w.road:
            if channel == "mobile_app":
                road_txt = title(w.road)
            else:
                road_txt = render_road(w.road, rng, prof["abbrev"], prof["town_abbrev"], tags)
            street_part = f"{blk_prefix(ptype, rng)}{w.blk} {road_txt}" if w.blk else road_txt
        else:
            street_part = f"{blk_prefix(ptype, rng)}{w.blk}" if w.blk else ""
        if channel == "marketplace" and w.road and rng.random() < prof["truncate"] and len(street_part) > 22:
            street_part = street_part[: rng.randint(16, len(street_part) - 3)].rstrip()
            tags.append("STREET_TRUNCATED")
            w.states["street"] = "truncated"
            w.road = self._truncated_road(street_part, w)
        building = title(w.building) if w.building else ""
        if w.postal:
            postal = w.postal
            if postal.startswith("0") and rng.random() < prof["leading_zero"]:
                postal = postal[1:]
                tags.append("POSTAL_LEADING_ZERO_LOST")
        else:
            postal = ""
        hint = rng.choice(LOCATION_HINTS) if rng.random() < prof["location_hint"] else ""
        if hint:
            tags.append("LOCATION_HINT")
        fields = {"address_line1": "", "address_line2": "", "postal_field": ""}

        if channel == "web_form":
            a1 = street_part or building
            a2_parts = [building] if building and street_part else []
            if unit and rng.random() < 0.3:
                a1 = f"{a1} {unit}" if rng.random() < 0.6 else f"{unit} {a1}"
            elif unit:
                a2_parts.insert(0, unit)
            if hint:
                a2_parts.append(hint)
            if rng.random() < prof["inline_noise"]:
                a2_parts.append(f"HP {phone(rng)}")
                tags.append("NOISE_PHONE")
            a2 = " ".join(a2_parts)
            if rng.random() < prof["duplicate"] and a1:
                a2 = a1 if not a2 else f"{a2} {a1}"
                tags.append("DUPLICATED_TEXT")
            case = {"as_is": 55, "lower": 25, "upper": 15, "mixed": 5}
            a1, a2 = case_style(a1, rng, case), case_style(a2, rng, case)
            pf = postal_text(postal, rng, {"{p}": 80, "S{p}": 5, "Singapore {p}": 10, "S {p}": 5}) if postal else ""
            fields.update(address_line1=a1, address_line2=a2, postal_field=pf)
            parts = [a1, a2] + (["Singapore"] if rng.random() < 0.5 and "SINGAPORE" not in pf.upper() else []) + [pf]
            text = ", ".join(x for x in parts if x)
        elif channel == "mobile_app":
            a1 = street_part
            a2 = " ".join(x for x in (unit, building, hint) if x)
            if rng.random() < prof["inline_noise"]:
                a2 = f"{a2} call {phone(rng)}".strip()
                tags.append("NOISE_PHONE")
            fields.update(address_line1=a1, address_line2=a2, postal_field=postal)
            text = ", ".join(x for x in (a1, a2, f"Singapore {postal}" if postal else "") if x)
        elif channel == "chat":
            addr_bits = [street_part]
            if unit:
                addr_bits.insert(rng.choice([0, 1]), unit)
            if building:
                addr_bits.append(building)
            if hint:
                addr_bits.append(hint)
            if postal:
                addr_bits.append(postal_text(postal, rng, {"{p}": 4, "S{p}": 3, "s{p}": 2, "S({p})": 1,
                                                          "Singapore {p}": 3, "spore {p}": 1, "sg {p}": 1}))
            addr = case_style(" ".join(x for x in addr_bits if x), rng, {"as_is": 3, "lower": 6, "upper": 1, "mixed": 1})
            if rng.random() < 0.3:
                addr = addr.replace(" #", ", #").replace(" Singapore", ", Singapore")
            lines = [addr]
            name = rng.choice(NAMES)
            extra = []
            if rng.random() < 0.8:
                extra.append(weighted(rng, {name: 3, f"Name: {name}": 2, f"to {name}": 1}))
                tags.append("NOISE_NAME")
            if rng.random() < 0.8:
                extra.append(weighted(rng, {phone(rng): 3, f"hp {phone(rng)}": 2, f"Contact: {phone(rng)}": 1}))
                tags.append("NOISE_PHONE")
            lines = extra[:1] + lines + extra[1:] if rng.random() < 0.7 else lines + extra
            if rng.random() < 0.4:
                lines.append(rng.choice(NOTES))
                tags.append("NOISE_NOTE")
            sep = weighted(rng, {"\n": 6, ", ": 2, " ": 2})
            text = sep.join(lines)
            fields.update(address_line1=text)
        elif channel == "marketplace":
            a1 = " ".join(x for x in (street_part, unit) if x)
            a2 = building
            region = weighted(rng, {"SINGAPORE": 5, "SINGAPORE, SINGAPORE": 3, "SG, SINGAPORE": 1})
            if rng.random() >= prof["duplicate"]:
                region = "SINGAPORE"
            elif region != "SINGAPORE":
                tags.append("DUPLICATED_TEXT")
            text = ", ".join(x for x in (a1, a2, hint, region, postal) if x).upper()
            if rng.random() < prof["inline_noise"]:
                n = f"{rng.choice('89')}{rng.randint(0, 9999999):07d}"
                text += f" (+65) {n[:4]} {n[4:]}"
                tags.append("NOISE_PHONE")
            fields.update(address_line1=a1.upper(), address_line2=a2.upper(), postal_field=postal)
        else:  # b2b_upload
            a1 = street_part
            if building and a1:
                a1 = f"{building}, {a1}" if rng.random() < 0.5 else f"{a1}, {building}"
            elif building:
                a1 = building
            if unit:
                a1 = f"{unit} {a1}" if rng.random() < 0.4 else f"{a1} {unit}"
            head = []
            if rng.random() < prof["inline_noise"]:
                head.append(rng.choice(COMPANIES))
                tags.append("NOISE_COMPANY")
                if rng.random() < 0.5:
                    head.append(f"Attn: {rng.choice(NAMES)}")
                    tags.append("NOISE_NAME")
            fields.update(address_line1=a1, postal_field=postal)
            text = ", ".join(head + [a1] + ([f"Singapore {postal}" if rng.random() < 0.5 else postal] if postal else []))
        return text, fields

    def _truncated_road(self, street_part: str, w: Written) -> str | None:
        """截断后标注员看到的道路：去掉楼栋号前缀，剩下的半截路名。"""
        toks = street_part.upper().split()
        toks = [t for t in toks if t not in ("BLK", "BLOCK", "BLK.") and t != (w.blk or "").upper()
                and not t.startswith("BLK")]
        return " ".join(toks) or None

    # ---- 组装一行
    def row(self, channel, fields, text, e, ptype, truth_unit, label, why, tags, st, truth=None) -> dict:
        unit_required = ptype in ("HDB", "CONDO", "COMMERCIAL")
        gold, acceptable = gold_action(label, tags, unit_required and "UNIT_MISSING" in tags)
        if e is not None:
            truth = {"blk": e.blk, "road": e.road, "postal": e.postal, "building": self.w.building_name(e) or ""}
        truth = truth or {"blk": "", "road": "", "postal": "", "building": ""}
        return {
            "channel": channel, "address_line1": fields["address_line1"], "address_line2": fields["address_line2"],
            "postal_field": fields["postal_field"], "input": text,
            "truth_eid": "" if e is None else e.eid, "truth_blk": truth["blk"], "truth_street": truth["road"],
            "truth_postal": truth["postal"], "truth_building": truth["building"], "truth_unit": std_unit(truth_unit),
            "property_type": ptype, "unit_required": "Y" if unit_required else "N",
            "text_resolution": label, "gold_action": gold, "acceptable_actions": "|".join(acceptable),
            "error_tags": "|".join(dict.fromkeys(tags)),
            "field_states": ";".join(f"{k}={v}" for k, v in st.items()),
            "label_note": why,
        }


def gold_action(label: str, tags: list[str], unit_missing: bool) -> tuple[str, list[str]]:
    """标注规范第 3 节：按"文字能判断到什么程度"和"需要改动什么"给出 BALANCED 档的期望结论。"""
    if label in (NOT_IN_REFERENCE,):
        return FIX, [FIX, CONFIRM]
    if label in (OUT_OF_REGION, NO_ADDRESS):
        return FIX, [FIX]
    if label == AMBIGUOUS:
        return FIX, [FIX, CONFIRM]
    if label == CONFLICTING:
        return CONFIRM, [CONFIRM, FIX]
    if label == MISLEADING:
        # 文字自洽地指向另一个真实地址：仅凭文字发现不了，按文字给期望结论，评测时单独统计
        return (ADD_SUB if unit_missing else ACCEPT), [ACCEPT, CONFIRM, ADD_SUB]
    if "CHINESE_ADDRESS" in tags:
        return CONFIRM, [CONFIRM, ADD_SUB] if unit_missing else [CONFIRM]
    major = [t for t in tags if t in MAJOR_TAGS]
    if major:
        ok = [CONFIRM] + ([ADD_SUB] if unit_missing else [])
        if all(t in MINOR_TAGS for t in major) and not unit_missing:
            ok.append(ACCEPT)
        return CONFIRM, ok
    if unit_missing:
        return ADD_SUB, [ADD_SUB, CONFIRM]
    return ACCEPT, [ACCEPT]


def split_of(key: str, test_share: float) -> str:
    h = int(hashlib.sha1(key.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "test" if h < test_share else "train"


def generate(world: World, n: int, seed: int, test_share: float = 0.4) -> list[dict]:
    gen = Generator(world, seed)
    rows = []
    for k in range(n):
        channel = weighted(gen.rng, CHANNELS)
        prof = PROFILES[channel]
        r = gen.rng.random()
        if r < prof["no_address"]:
            row = gen.no_address(channel, prof)
        elif r < prof["no_address"] + prof["out_of_region"]:
            row = gen.out_of_region(channel, prof)
        elif r < prof["no_address"] + prof["out_of_region"] + prof["not_in_ref"]:
            row = gen.not_in_reference(channel, prof)
        else:
            row = gen.regular(channel, prof)
        oid = f"ORD-{k + 1:05d}"
        # 按真实地址切分训练 / 测试，同一地址的订单不会同时出现在两边
        key = str(row["truth_eid"]) if row["truth_eid"] != "" else f"{row['truth_street']}|{row['truth_blk']}|{oid}"
        rows.append({"order_id": oid, "split": split_of(key, test_share), **row})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", default=str(ROOT / "data" / "reference_sg.csv.gz"))
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=20261015)
    ap.add_argument("--test-share", type=float, default=0.4)
    ap.add_argument("--out", default=str(ROOT / "labeled" / "orders_sg_v1.csv"))
    args = ap.parse_args()

    rows = generate(World(ReferenceDB.load(args.reference)), args.n, args.seed, args.test_share)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} 单 -> {out}")
    for col in ("split", "channel", "property_type", "text_resolution", "gold_action"):
        print(f"  {col}: {dict(Counter(r[col] for r in rows).most_common())}")
    tags = Counter(t for r in rows for t in r["error_tags"].split("|") if t)
    print(f"  error_tags: {dict(tags.most_common())}")


if __name__ == "__main__":
    main()
