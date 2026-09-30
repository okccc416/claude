"""目标市场配置：每个市场的试点城市范围、地址类别与写法特征。

类别（见 docs/12）：
  A  有开放官方地址表、写法规则：逐门牌验真（澳洲、德国、法国、荷兰；新加坡用专用引擎）
  B  中东：没有开放地址表，阿拉伯文 / 英文混写，地标式描述，各国自有编码
  C  东南亚其他国家：没有开放地址表，邮编只到片区，多语种、多文字
B / C 类用地图数据（道路、行政区、楼宇 / POI）验真到道路 / 楼宇 / 片区粒度。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Market:
    code: str
    name: str
    cls: str  # "A" / "B" / "C"
    regions: tuple[tuple[str, tuple[float, float, float, float]], ...]  # (城市, (xmin, ymin, xmax, ymax))
    postcode: str | None  # 邮编正则（None = 基本不用邮编）
    number_first: bool = True  # 门牌号写在道路名前面（12 Smith St）还是后面（Smithstraße 12）
    languages: tuple[str, ...] = ("en",)
    notes: str = ""
    abbreviations: dict[str, tuple[str, ...]] = field(default_factory=dict)  # 规范词 -> 常见写法


EN_ROAD = {
    "STREET": ("ST", "STR"), "ROAD": ("RD",), "AVENUE": ("AVE", "AV"), "DRIVE": ("DR", "DRV"),
    "PLACE": ("PL",), "LANE": ("LN",), "CRESCENT": ("CRES", "CR"), "COURT": ("CT",), "PARADE": ("PDE",),
    "HIGHWAY": ("HWY",), "BOULEVARD": ("BLVD",), "TERRACE": ("TCE", "TER"), "CLOSE": ("CL",), "SQUARE": ("SQ",),
    "CIRCUIT": ("CCT", "CT"), "GROVE": ("GR", "GRV"), "WAY": ("WY",), "ESPLANADE": ("ESP",), "NORTH": ("N", "NTH"),
    "SOUTH": ("S", "STH"), "EAST": ("E",), "WEST": ("W",), "MOUNT": ("MT",), "SAINT": ("ST",),
}

MARKETS: dict[str, Market] = {m.code: m for m in [
    Market("AU", "澳大利亚", "A", (("悉尼", (150.9, -34.1, 151.35, -33.7)), ("墨尔本", (144.8, -37.95, 145.2, -37.65))),
           r"\b\d{4}\b", True, ("en",), "门牌可带单元：Unit 5/12 或 5/12；州缩写 NSW / VIC", EN_ROAD),
    Market("DE", "德国", "A", (("柏林", (13.08, 52.33, 13.77, 52.68)),), r"\b\d{5}\b", False, ("de",),
           "门牌在道路名后：Musterstraße 12；Straße 常写作 Str.",
           {"STRASSE": ("STR", "STRAßE", "STRASE"), "PLATZ": ("PL",), "ALLEE": (), "WEG": (), "DAMM": ()}),
    Market("FR", "法国", "A", (("巴黎", (2.22, 48.81, 2.47, 48.91)),), r"\b\d{5}\b", True, ("fr",),
           "12 rue de …；bis / ter 后缀", {"RUE": ("R",), "AVENUE": ("AV", "AVE"), "BOULEVARD": ("BD", "BLVD"),
                                          "PLACE": ("PL",), "SAINT": ("ST",), "SAINTE": ("STE",), "QUAI": ("QU",)}),
    Market("NL", "荷兰", "A", (("阿姆斯特丹", (4.72, 52.28, 5.08, 52.43)),), r"\b\d{4}\s?[A-Z]{2}\b", False, ("nl",),
           "门牌在道路名后，可带字母：Rozengracht 162A；邮编 1234 AB", {"STRAAT": ("STR",), "PLEIN": (), "GRACHT": ()}),
    Market("AE", "阿联酋", "B", (("迪拜", (55.05, 24.9, 55.6, 25.35)),), None, True, ("en", "ar"),
           "没有邮编；楼名 + 区域为主；Makani 10 位号码", EN_ROAD),
    Market("SA", "沙特", "B", (("利雅得", (46.45, 24.45, 47.0, 25.0)),), r"\b\d{5}\b", True, ("ar", "en"),
           "国家地址：4 位楼号 + 街道 + 区 + 5 位邮编；短码如 RCTB4359", EN_ROAD),
    Market("MY", "马来西亚", "C", (("吉隆坡", (101.55, 3.0, 101.8, 3.25)),), r"\b\d{5}\b", True, ("ms", "en"),
           "Jalan / Jln；Lot、No.；Taman、Bandar 片区",
           {"JALAN": ("JLN", "JL"), "LORONG": ("LOR", "LRG"), "PERSIARAN": ("PSN",), "LEBUH": ("LBH",),
            "TAMAN": ("TMN",), "BANDAR": ("BDR",), "KAMPUNG": ("KG", "KPG"), "BUKIT": ("BT", "BKT")}),
    Market("ID", "印尼", "C", (("雅加达", (106.68, -6.37, 106.98, -6.08)),), r"\b\d{5}\b", False, ("id",),
           "Jl. 道路 No. 门牌；RT/RW；Kelurahan / Kecamatan",
           {"JALAN": ("JL", "JLN"), "GANG": ("GG",), "NOMOR": ("NO",), "KELURAHAN": ("KEL",),
            "KECAMATAN": ("KEC",), "RAYA": ("RY",)}),
    Market("TH", "泰国", "C", (("曼谷", (100.4, 13.6, 100.75, 13.95)),), r"\b\d{5}\b", True, ("th", "en"),
           "门牌 112/55；Soi（ซอย）/ Road（ถนน）；Khwaeng / Khet",
           {"ROAD": ("RD",), "SOI": ("ซ", "ซอย"), "THANON": ("ถ", "ถนน")}),
    Market("VN", "越南", "C", (("胡志明市", (106.6, 10.7, 106.8, 10.9)),), r"\b\d{6}\b", True, ("vi",),
           "339/5 Tô Hiến Thành；Đường / Phường / Quận",
           {"DUONG": ("D", "Đ", "ĐƯỜNG"), "PHUONG": ("P", "PHƯỜNG"), "QUAN": ("Q", "QUẬN")}),
    Market("PH", "菲律宾", "C", (("马尼拉", (120.95, 14.5, 121.1, 14.7)),), r"\b\d{4}\b", True, ("en", "tl"),
           "Barangay；St.；1300 Metro Manila", EN_ROAD),
]}
