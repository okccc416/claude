"""目标市场配置：每个市场的试点城市范围、地址类别与写法特征。

类别（见 docs/12、docs/13）：
  A  有开放官方地址表：逐门牌验真（新加坡用专用引擎；其余见下表 cls="A"）
  B  中东：没有开放地址表，阿拉伯文 / 英文混写，地标式描述，各国自有编码
  C  其他没有开放地址表的市场（东南亚、英国、爱尔兰、瑞典、匈牙利、保加利亚、阿根廷、印度、波多黎各）
B / C 类用地图数据（道路、行政区、楼宇 / POI）验真到道路 / 楼宇 / 片区粒度。
覆盖范围：Google Address Validation 覆盖的全部国家 / 地区（美国除外），外加中东和东南亚。
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
    abbreviations: dict[str, tuple[str, ...]] = field(default_factory=dict)  # 规范词 -> 常见写法（说明用）
    postcode_first: bool = False  # 邮编写在城市前面（欧洲：10115 Berlin）
    omit_type: bool = False  # 常省略道路类型词（Jalan / ulica / tänav …）：允许去掉类型词后匹配
    type_after: bool = False  # 英文式写法：类型词在名称后面（King Street）
    hash_number: bool = False  # "#" 标门牌号（拉美：Calle 26 # 13-19、Reforma #222），而不是单元号
    pc_rule: str = ""  # 邮编识别：""（取最后一个）/ "end"（只认末尾或州名后，澳洲式）/ "chunk"（未知邮编须单独成段）
    city_words: tuple[str, ...] = ()  # 单独成段时不作片区证据的全城名 / 国家名
    region_words: tuple[str, ...] = ()  # 任何位置都不参与匹配的州 / 大区名
    cities: tuple[str, ...] = ()  # 合成地址里的城市写法
    unit_fmt: tuple[str, ...] = ()  # 合成地址里的单元写法
    state: str = ""  # 排版用的州 / 省缩写（加拿大：Toronto ON M5V 2K4）


EN_ROAD = {
    "STREET": ("ST", "STR"), "ROAD": ("RD",), "AVENUE": ("AVE", "AV"), "DRIVE": ("DR", "DRV"),
    "PLACE": ("PL",), "LANE": ("LN",), "CRESCENT": ("CRES", "CR"), "COURT": ("CT",), "PARADE": ("PDE",),
    "HIGHWAY": ("HWY",), "BOULEVARD": ("BLVD",), "TERRACE": ("TCE", "TER"), "CLOSE": ("CL",), "SQUARE": ("SQ",),
    "CIRCUIT": ("CCT", "CT"), "GROVE": ("GR", "GRV"), "WAY": ("WY",), "ESPLANADE": ("ESP",), "NORTH": ("N", "NTH"),
    "SOUTH": ("S", "STH"), "EAST": ("E",), "WEST": ("W",), "MOUNT": ("MT",), "SAINT": ("ST",),
}

MARKETS: dict[str, Market] = {m.code: m for m in [
    Market("AU", "澳大利亚", "A", (("悉尼", (150.9, -34.1, 151.35, -33.7)), ("墨尔本", (144.8, -37.95, 145.2, -37.65))),
           r"\b\d{4}\b", True, ("en",), "门牌可带单元：Unit 5/12 或 5/12；州缩写 NSW / VIC", EN_ROAD,
           type_after=True),
    Market("DE", "德国", "A", (("柏林", (13.08, 52.33, 13.77, 52.68)),), r"\b\d{5}\b", False, ("de",),
           "门牌在道路名后：Musterstraße 12；Straße 常写作 Str.",
           {"STRASSE": ("STR", "STRAßE", "STRASE"), "PLATZ": ("PL",), "ALLEE": (), "WEG": (), "DAMM": ()},
           postcode_first=True),
    Market("FR", "法国", "A", (("巴黎", (2.22, 48.81, 2.47, 48.91)),), r"\b\d{5}\b", True, ("fr",),
           "12 rue de …；bis / ter 后缀", {"RUE": ("R",), "AVENUE": ("AV", "AVE"), "BOULEVARD": ("BD", "BLVD"),
                                          "PLACE": ("PL",), "SAINT": ("ST",), "SAINTE": ("STE",), "QUAI": ("QU",)},
           postcode_first=True),
    Market("NL", "荷兰", "A", (("阿姆斯特丹", (4.72, 52.28, 5.08, 52.43)),), r"\b\d{4}\s?[A-Z]{2}\b", False, ("nl",),
           "门牌在道路名后，可带字母：Rozengracht 162A；邮编 1234 AB", {"STRAAT": ("STR",), "PLEIN": (), "GRACHT": ()},
           postcode_first=True),
    Market("AE", "阿联酋", "B", (("迪拜", (55.05, 24.9, 55.6, 25.35)),), None, True, ("en", "ar"),
           "没有邮编；楼名 + 区域为主；Makani 10 位号码", EN_ROAD, omit_type=True, type_after=True),
    Market("SA", "沙特", "B", (("利雅得", (46.45, 24.45, 47.0, 25.0)),), r"\b\d{5}\b", True, ("ar", "en"),
           "国家地址：4 位楼号 + 街道 + 区 + 5 位邮编；短码如 RCTB4359", EN_ROAD, omit_type=True, type_after=True),
    Market("MY", "马来西亚", "C", (("吉隆坡", (101.55, 3.0, 101.8, 3.25)),), r"\b\d{5}\b", True, ("ms", "en"),
           "Jalan / Jln；Lot、No.；Taman、Bandar 片区",
           {"JALAN": ("JLN", "JL"), "LORONG": ("LOR", "LRG"), "PERSIARAN": ("PSN",), "LEBUH": ("LBH",),
            "TAMAN": ("TMN",), "BANDAR": ("BDR",), "KAMPUNG": ("KG", "KPG"), "BUKIT": ("BT", "BKT")},
           omit_type=True),
    Market("ID", "印尼", "C", (("雅加达", (106.68, -6.37, 106.98, -6.08)),), r"\b\d{5}\b", False, ("id",),
           "Jl. 道路 No. 门牌；RT/RW；Kelurahan / Kecamatan",
           {"JALAN": ("JL", "JLN"), "GANG": ("GG",), "NOMOR": ("NO",), "KELURAHAN": ("KEL",),
            "KECAMATAN": ("KEC",), "RAYA": ("RY",)}, omit_type=True),
    Market("TH", "泰国", "C", (("曼谷", (100.4, 13.6, 100.75, 13.95)),), r"\b\d{5}\b", True, ("th", "en"),
           "门牌 112/55；Soi（ซอย）/ Road（ถนน）；Khwaeng / Khet",
           {"ROAD": ("RD",), "SOI": ("ซ", "ซอย"), "THANON": ("ถ", "ถนน")}, omit_type=True),
    Market("VN", "越南", "C", (("胡志明市", (106.6, 10.7, 106.8, 10.9)),), r"\b\d{5,6}\b", True, ("vi",),
           "339/5 Tô Hiến Thành；Đường / Phường / Quận；邮编 2018 年起为 5 位（旧版 6 位仍常见）",
           {"DUONG": ("D", "Đ", "ĐƯỜNG"), "PHUONG": ("P", "PHƯỜNG"), "QUAN": ("Q", "QUẬN")}, omit_type=True),
    Market("PH", "菲律宾", "C", (("马尼拉", (120.95, 14.5, 121.1, 14.7)),), r"\b\d{4}\b", True, ("en", "tl"),
           "Barangay；St.；1300 Metro Manila", EN_ROAD, type_after=True),
]}

# ---------------------------------------------------------------------------------------------------------------
# Google Address Validation 覆盖的其余国家 / 地区（美国除外）。每个国家先建一个试点城市（首都或最大的商业城市）。
# A 类：Overture 里有官方地址表（加拿大 StatCan ODA、巴西 IBGE CNEFE、墨西哥 INEGI、日本 住所基礎、欧洲各国地籍 / 地址登记）
# C 类：没有开放地址表（英国、爱尔兰、瑞典、匈牙利、保加利亚、阿根廷、印度、波多黎各）
EU = dict(postcode_first=True)
_GOOGLE = [
    # —— 美洲
    Market("CA", "加拿大", "A", (("多伦多", (-79.55, 43.58, -79.20, 43.80)),), r"\b[ABCEGHJ-NPRSTVXY]\d[A-Z]\s?\d[A-Z]\d\b",
           True, ("en",), "123 King St W；单元写作 Suite 200 / #1203 / 1203-100 King St", EN_ROAD, type_after=True,
           city_words=("TORONTO", "CANADA"), region_words=("ONTARIO",), cities=("Toronto", "Toronto, ON"),
           unit_fmt=("Suite {u}", "Unit {u}", "#{u}"), state="ON"),
    Market("MX", "墨西哥", "A", (("墨西哥城", (-99.25, 19.30, -99.05, 19.50)),), r"\b\d{5}\b", False, ("es",),
           "Calle Durango 68, Col. Roma Norte, 06700 CDMX；常省略 Calle；# 标门牌", omit_type=True, hash_number=True,
           city_words=("CIUDAD DE MEXICO", "CDMX", "MEXICO CITY", "MEXICO DF", "DF", "MEXICO", "CMX"),
           cities=("Ciudad de México", "CDMX"), unit_fmt=("Int. {u}", "Piso {f}", "Local {u}")),
    Market("PR", "波多黎各", "C", (("圣胡安", (-66.20, 18.33, -65.95, 18.48)),), r"\b00[679]\d{2}(?:-\d{4})?\b", True,
           ("es", "en"), "美式写法：1503 Calle Loíza / 1250 Ave. Ponce de León；邮编 009xx",
           city_words=("SAN JUAN", "PUERTO RICO", "PR"), cities=("San Juan", "San Juan, PR"),
           unit_fmt=("Suite {u}", "Apt {u}", "Local {u}")),
    Market("BR", "巴西", "A", (("圣保罗", (-46.78, -23.65, -46.52, -23.48)),), r"\b\d{5}-?\d{3}\b", False, ("pt",),
           "Av. Paulista, 1578 - Bela Vista, São Paulo - SP, 01310-200", **EU,
           city_words=("SAO PAULO", "SAO PAULO SP", "SP", "BRASIL", "BRAZIL"), cities=("São Paulo", "São Paulo - SP"),
           unit_fmt=("Sala {u}", "{f}º andar", "Loja {u}", "Apto {u}")),
    Market("AR", "阿根廷", "C", (("布宜诺斯艾利斯", (-58.53, -34.71, -58.33, -34.53)),),
           r"\b[A-HJ-NP-Z]\d{4}(?:[A-Z]{3})?\b", False, ("es",), "Av. Corrientes 1234, C1043AAZ CABA；门牌常为 4 位",
           **EU, omit_type=True, hash_number=True,
           city_words=("CABA", "BUENOS AIRES", "CIUDAD AUTONOMA DE BUENOS AIRES", "CIUDAD DE BUENOS AIRES", "ARGENTINA"),
           cities=("CABA", "Buenos Aires"), unit_fmt=("Piso {f}", "Dto. {b}", "Local {u}")),
    Market("CL", "智利", "A", (("圣地亚哥", (-70.75, -33.55, -70.50, -33.35)),), r"\b\d{7}\b", False, ("es",),
           "Moneda 788, Santiago；Av. Providencia 1234", omit_type=True, hash_number=True,
           city_words=("SANTIAGO", "REGION METROPOLITANA", "CHILE", "SANTIAGO DE CHILE"), cities=("Santiago",),
           unit_fmt=("Of. {u}", "Piso {f}", "Local {u}")),
    Market("CO", "哥伦比亚", "A", (("波哥大", (-74.20, 4.50, -74.00, 4.80)),), r"\b\d{6}\b", False, ("es",),
           "Calle 72 # 8-24（街道编号 + 交叉街编号 - 距离）；Cra. / Cl. / Kr / Ak", hash_number=True,
           city_words=("BOGOTA", "BOGOTA DC", "DC", "COLOMBIA", "BOGOTA DISTRITO CAPITAL"),
           cities=("Bogotá", "Bogotá D.C."), unit_fmt=("Piso {f}", "Oficina {u}", "Local {u}")),
    # —— 欧洲
    Market("GB", "英国", "C", (("伦敦", (-0.30, 51.43, 0.05, 51.58)),), r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b", True,
           ("en",), "17 Leicester Square, London WC2H 7AS；邮编精确到十几户", EN_ROAD, type_after=True,
           city_words=("LONDON", "GREATER LONDON", "UK", "UNITED KINGDOM", "ENGLAND"),
           region_words=("UNITED KINGDOM", "GREAT BRITAIN"), cities=("London",),
           unit_fmt=("Flat {u}", "Unit {u}", "Suite {u}")),
    Market("IE", "爱尔兰", "C", (("都柏林", (-6.40, 53.28, -6.10, 53.42)),),
           r"\b[ACDEFHKNPRTVWXY]\d[\dW]\s?[0-9ACDEFHKNPRTVWXY]{4}\b", True, ("en",), "35 Molesworth Street, Dublin 2, D02 A023",
           EN_ROAD, type_after=True, city_words=("DUBLIN", "CO DUBLIN", "COUNTY DUBLIN", "IRELAND"),
           cities=("Dublin", "Co. Dublin"), unit_fmt=("Unit {u}", "Apartment {u}", "Suite {u}")),
    Market("BE", "比利时", "A", (("布鲁塞尔", (4.25, 50.76, 4.48, 50.92)),), r"\b\d{4}\b", False, ("fr", "nl"),
           "Rue de la Loi 16, 1000 Bruxelles（法 / 荷双语路名，门牌在后）", **EU, pc_rule="chunk",
           city_words=("BRUXELLES", "BRUSSEL", "BRUSSELS", "BELGIQUE", "BELGIE", "BELGIUM"),
           cities=("Bruxelles", "Brussel"), unit_fmt=("bte {u}", "bus {u}")),
    Market("LU", "卢森堡", "A", (("卢森堡市", (5.85, 49.50, 6.30, 49.75)),), r"\b(?:L-?)?\d{4}\b", True, ("fr",),
           "7 Rue de Prague, L-2348 Luxembourg", **EU, pc_rule="chunk",
           city_words=("LUXEMBOURG", "LUXEMBURG", "LETZEBUERG"), cities=("Luxembourg",), unit_fmt=("Bte {u}",)),
    Market("CH", "瑞士", "A", (("苏黎世", (8.44, 47.32, 8.63, 47.43)),), r"\b(?:CH-?)?\d{4}\b", False, ("de",),
           "Bahnhofstrasse 1, 8001 Zürich（瑞士写 ss）", **EU, pc_rule="chunk",
           city_words=("ZURICH", "SCHWEIZ", "SWITZERLAND", "SUISSE"), cities=("Zürich",)),
    Market("AT", "奥地利", "A", (("维也纳", (16.18, 48.12, 16.58, 48.32)),), r"\b(?:A-?)?\d{4}\b", False, ("de",),
           "Mariahilfer Straße 120, 1070 Wien；Stiege / Top 单元", **EU, pc_rule="chunk",
           city_words=("WIEN", "VIENNA", "OSTERREICH", "AUSTRIA"), cities=("Wien",), unit_fmt=("Top {u}", "Stiege {b}")),
    Market("IT", "意大利", "A", (("米兰", (9.04, 45.39, 9.28, 45.54)),), r"\b\d{5}\b", False, ("it",),
           "Via Torino 28, 20123 Milano MI；V.le / C.so / P.za 缩写", **EU,
           city_words=("MILANO", "MILAN", "MILANO MI", "MI", "ITALIA", "ITALY"), cities=("Milano", "Milano MI"),
           unit_fmt=("Scala {b}", "Piano {f}", "Int. {u}")),
    Market("ES", "西班牙", "A", (("马德里", (-3.80, 40.32, -3.58, 40.52)),), r"\b\d{5}\b", False, ("es",),
           "C/ Mayor, 12, 3º B, 28013 Madrid", **EU, city_words=("MADRID", "ESPANA", "SPAIN"), cities=("Madrid",),
           unit_fmt=("{f}º {b}", "Piso {f}", "Local {u}")),
    Market("PT", "葡萄牙", "A", (("里斯本", (-9.25, 38.69, -9.08, 38.80)),), r"\b\d{4}-\d{3}\b", False, ("pt",),
           "Rua Augusta 12, 1100-048 Lisboa；R. / Av. / Tv. / Lg. 缩写", **EU,
           city_words=("LISBOA", "LISBON", "PORTUGAL"), cities=("Lisboa",), unit_fmt=("{f}º Esq", "{f}º Dto", "Loja {u}")),
    Market("DK", "丹麦", "A", (("哥本哈根", (12.45, 55.61, 12.65, 55.73)),), r"\b(?:DK-?)?\d{4}\b", False, ("da",),
           "Vesterbrogade 2, 1620 København V；楼层 st. / 2. th", **EU, pc_rule="chunk",
           city_words=("KOBENHAVN", "COPENHAGEN", "DANMARK", "DENMARK", "KOBENHAVN K", "KOBENHAVN V", "KOBENHAVN O",
                       "KOBENHAVN N", "KOBENHAVN S", "KOBENHAVN NV", "KOBENHAVN SV"),
           cities=("København", "København K"), unit_fmt=("{f}. th", "{f}. tv", "st.")),
    Market("SE", "瑞典", "C", (("斯德哥尔摩", (17.90, 59.25, 18.20, 59.40)),), r"\b\d{3}\s?\d{2}\b", False, ("sv",),
           "Drottninggatan 85, 111 61 Stockholm", **EU, city_words=("STOCKHOLM", "SVERIGE", "SWEDEN"),
           cities=("Stockholm",), unit_fmt=("lgh {u}",)),
    Market("NO", "挪威", "A", (("奥斯陆", (10.62, 59.85, 10.90, 59.98)),), r"\b\d{4}\b", False, ("no",),
           "Karl Johans gate 1, 0154 Oslo", **EU, pc_rule="chunk", city_words=("OSLO", "NORGE", "NORWAY"),
           cities=("Oslo",)),
    Market("FI", "芬兰", "A", (("赫尔辛基", (24.80, 60.13, 25.15, 60.27)),), r"\b\d{5}\b", False, ("fi", "sv"),
           "Mannerheimintie 12, 00100 Helsinki（芬兰语 / 瑞典语路名）", **EU,
           city_words=("HELSINKI", "HELSINGFORS", "SUOMI", "FINLAND"), cities=("Helsinki",), unit_fmt=("A {u}", "B {u}")),
    Market("EE", "爱沙尼亚", "A", (("塔林", (24.55, 59.35, 24.95, 59.50)),), r"\b\d{5}\b", False, ("et",),
           "Pikk tn 33, 10133 Tallinn；常省略 tänav", **EU, omit_type=True,
           city_words=("TALLINN", "EESTI", "ESTONIA", "HARJU MAAKOND", "HARJUMAA"), cities=("Tallinn",)),
    Market("LV", "拉脱维亚", "A", (("里加", (23.95, 56.88, 24.30, 57.05)),), r"\bLV-?\d{4}\b", False, ("lv",),
           "Brīvības iela 33, Rīga, LV-1010", **EU, omit_type=True, city_words=("RIGA", "LATVIJA", "LATVIA"),
           cities=("Rīga",)),
    Market("LT", "立陶宛", "A", (("维尔纽斯", (25.15, 54.62, 25.40, 54.78)),), r"\b(?:LT-?)?\d{5}\b", False, ("lt",),
           "Gedimino pr. 9, LT-01103 Vilnius；g. = gatvė", **EU, omit_type=True,
           city_words=("VILNIUS", "LIETUVA", "LITHUANIA", "VILNIAUS M"), cities=("Vilnius",)),
    Market("PL", "波兰", "A", (("华沙", (20.85, 52.10, 21.20, 52.32)),), r"\b\d{2}-\d{3}\b", False, ("pl",),
           "ul. Marszałkowska 100/102, 00-026 Warszawa；常省略 ul.", **EU, omit_type=True,
           city_words=("WARSZAWA", "WARSAW", "POLSKA", "POLAND"), cities=("Warszawa",), unit_fmt=("lok. {u}", "m. {u}")),
    Market("CZ", "捷克", "A", (("布拉格", (14.30, 49.98, 14.65, 50.15)),), r"\b\d{3}\s?\d{2}\b", False, ("cs",),
           "Vodičkova 1935/38, 110 00 Praha 1（门牌 = 登记号 / 街道号）", **EU,
           city_words=("PRAHA", "PRAGUE", "CESKA REPUBLIKA", "CZECHIA", "CZECH REPUBLIC"), cities=("Praha", "Praha 1")),
    Market("SK", "斯洛伐克", "A", (("布拉迪斯拉发", (17.00, 48.08, 17.20, 48.22)),), r"\b\d{3}\s?\d{2}\b", False, ("sk",),
           "Obchodná 2132/1, 811 06 Bratislava（门牌 = 登记号 / 街道号）", **EU,
           city_words=("BRATISLAVA", "SLOVENSKO", "SLOVAKIA"), cities=("Bratislava",)),
    Market("HU", "匈牙利", "C", (("布达佩斯", (18.95, 47.40, 19.20, 47.58)),), r"\b\d{4}\b", False, ("hu",),
           "Andrássy út 12, 1061 Budapest；u. = utca、krt. = körút", **EU, pc_rule="chunk",
           city_words=("BUDAPEST", "MAGYARORSZAG", "HUNGARY"), cities=("Budapest",), unit_fmt=("{f}. em.",)),
    Market("SI", "斯洛文尼亚", "A", (("卢布尔雅那", (14.42, 46.00, 14.60, 46.11)),), r"\b(?:SI-?)?\d{4}\b", False, ("sl",),
           "Slovenska cesta 12, 1000 Ljubljana", **EU, pc_rule="chunk", omit_type=True,
           city_words=("LJUBLJANA", "SLOVENIJA", "SLOVENIA"), cities=("Ljubljana",)),
    Market("HR", "克罗地亚", "A", (("萨格勒布", (15.85, 45.75, 16.10, 45.85)),), r"\b(?:HR-?)?\d{5}\b", False, ("hr",),
           "Ilica 12, 10000 Zagreb；常省略 ulica", **EU, omit_type=True,
           city_words=("ZAGREB", "HRVATSKA", "CROATIA"), cities=("Zagreb",)),
    Market("BG", "保加利亚", "C", (("索非亚", (23.22, 42.62, 23.42, 42.75)),), r"\b\d{4}\b", False, ("bg", "en"),
           "ул. Пиротска 9, 1000 София；西里尔文 / 拉丁转写混写", **EU, pc_rule="chunk", omit_type=True,
           city_words=("SOFIA", "SOFIYA", "BULGARIA", "BALGARIYA", "GRAD SOFIYA"), cities=("София", "Sofia"),
           unit_fmt=("ет. {f}", "ап. {u}")),
    # —— 亚太
    Market("NZ", "新西兰", "A", (("奥克兰", (174.65, -36.95, 174.90, -36.80)),), r"\b\d{4}\b", True, ("en",),
           "Level 5, 35 Albert Street, Auckland Central, Auckland 1010", EN_ROAD, type_after=True, pc_rule="end",
           city_words=("AUCKLAND", "NEW ZEALAND", "NZ"), cities=("Auckland",),
           unit_fmt=("Unit {u}", "Level {f}", "Apartment {u}")),
    Market("JP", "日本", "A", (("东京", (139.65, 35.62, 139.82, 35.74)),), r"\b\d{3}-?\d{4}\b", False, ("ja",),
           "〒100-0005 東京都千代田区丸の内2丁目7-9（町丁目 + 番地-号，没有路名）", **EU,
           city_words=("東京都", "TOKYO", "JAPAN", "日本"), cities=("東京都",), unit_fmt=("{f}F", "{f}階")),
    Market("IN", "印度", "C", (("孟买", (72.80, 18.90, 72.98, 19.15)),), r"\b\d{3}\s?\d{3}\b", True, ("en",),
           "Shop 7, Silver Croft Building, Pali Hill, Bandra West, Mumbai 400050；楼名 + 地标为主", EN_ROAD,
           type_after=True, city_words=("MUMBAI", "BOMBAY", "INDIA"), region_words=("MAHARASHTRA",),
           cities=("Mumbai", "Mumbai, Maharashtra"), unit_fmt=("Shop No. {u}", "Flat {u}", "Office {u}")),
]
MARKETS.update({m.code: m for m in _GOOGLE})
