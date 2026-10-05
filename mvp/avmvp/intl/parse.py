"""把输入拆成组件：邮编、门牌、单元、道路、片区、楼宇 / POI、各国编码。

两种解析器，输出同一结构（Parsed），后面的验真与结论完全相同：
  RuleParser  规则 + 地名表：正则抽邮编 / 单元 / 编码，按参考库的道路名、片区名做最长匹配，再按市场语序找门牌
  CRFParser   机器学习：条件随机场给每个词打标签（见 crf.py），标签连成片段后再到参考库检索
混合方案：两者的候选一起送进验真层，由参考数据决定采用哪个解释。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .markets import MARKETS
from .reference import BUILDING_WORDS, MarketReference
from .text import (TYPE_WORDS, core_key, fold, key, merge_initials, norm_postcode, phrase_norm, script_of,
                   skeleton, tokenize, type_words)

from .noise import strip_noise as _strip_noise  # noqa: E402
# 单独出现时不能当楼名 / 转写道路名的通用词
GENERIC_WORDS = {"OFFICE", "SHOP", "BUILDING", "TOWER", "TOWERS", "MALL", "CENTER", "CENTRE", "HOTEL", "FLOOR",
                 "GROUND", "LEVEL", "SUITE", "UNIT", "STORE", "PLAZA", "MARKET", "SHOPPING", "COMMERCIAL",
                 "INDUSTRIAL", "AREA", "CITY", "COMPLEX", "RESIDENCE", "APARTMENTS", "VILLA", "WAREHOUSE", "THE",
                 "BUSINESS", "BOULEVARD", "CORNER", "EDIFICIO", "TORRE", "CENTRO", "COMERCIAL", "LOCAL", "OFICINA",
                 "PISO", "SALA", "LOJA", "HOUSE", "HAUS", "GEBAUDE", "PALAZZO", "CONDOMINIO", "GALERIA", "PASSAGE"}
UNIT_WORDS = {"UNIT", "APARTMENT", "SUITE", "SHOP", "FLAT", "LEVEL", "FLOOR", "LANTAI", "TANG", "ชั้น", "ห้อง",
              "الطابق", "شقه", "مكتب", "LOT", "ROOM", "KIOSK", "STALL", "OFFICE", "TOWER", "BLOCK", "BLOK",
              # 欧洲 / 拉美 / 日本的单元、楼层写法
              "PISO", "OFICINA", "LOCAL", "DEPARTAMENTO", "INTERIOR", "DESPACHO", "PLANTA", "APTO", "APARTAMENTO",
              "ANDAR", "SALA", "LOJA", "BLOCO", "CONJUNTO", "PIANO", "INTERNO", "SCALA", "ETAGE", "BUS", "BTE",
              "BOITE", "WHG", "WOHNUNG", "TOP", "STIEGE", "OG", "LGH", "LAGENHET", "LOKAL", "BYT", "EMELET", "AJTO",
              "KAT", "STAN", "ET", "AP", "APT",
              # 缩写原样（解析单元时还没展开缩写）
              "INT", "OF", "OFIC", "LOC", "DEPTO", "DPTO", "LJ", "SL", "UND", "LOK", "WHG", "BTE"}
# BL：保加利亚的楼号（ж.к. Младост 1, бл. 505 = 小区 + 楼号）
NUMBER_MARKERS = {"NO", "NOMOR", "NUMBER", "BLK", "#", "رقم", "مبني", "SỐ", "SO", "เลขที่", "VILLA", "فيلا", "BL"}
MARKER_WORDS = {"NO", "NOMOR", "NUMBER", "KAV", "KAVLING", "KM", "رقم", "BL"}
HOUSE_NO = re.compile(r"^\d{1,5}(?:[A-Z]|HS|BG|BV)?(?:[/\-]\d{1,5}[A-Z]?){0,2}$")
AU_STATES = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"}
FLOOR_TOKEN = re.compile(r"^(?:\d{1,2}(?:ST|ND|RD|TH)?F|G|GF|UG|LG|UGF|LGF|B\d)$")  # 2F、12F、GF：楼层，不是门牌
# 国家 / 州 / 大区名：不参与道路 / 片区匹配（避免 Metro Manila -> Metro Avenue、Selangor -> Jalan Selangor）
REGION_WORDS = {
    "AU": ["AUSTRALIA", "NEW SOUTH WALES", "VICTORIA"], "DE": ["DEUTSCHLAND", "GERMANY"],
    "FR": ["FRANCE"], "NL": ["NEDERLAND", "NETHERLANDS", "THE NETHERLANDS"],
    "AE": ["UAE", "UNITED ARAB EMIRATES", "الامارات العربيه المتحده", "الامارات"],
    "SA": ["SAUDI ARABIA", "KSA", "KINGDOM OF SAUDI ARABIA", "المملكه العربيه السعوديه", "السعوديه"],
    "MY": ["MALAYSIA", "SELANGOR", "SELANGOR DARUL EHSAN", "WILAYAH PERSEKUTUAN"],
    "ID": ["INDONESIA", "DKI JAKARTA", "DKI", "DAERAH KHUSUS IBUKOTA", "JAWA BARAT", "BANTEN"],
    "TH": ["THAILAND", "ประเทศไทย"], "VN": ["VIETNAM", "VIET NAM"],
    "PH": ["PHILIPPINES", "METRO MANILA", "NCR", "NATIONAL CAPITAL REGION"],
}
# 覆盖整个试点范围的城市名：单独成段时（", Riyadh,"）不作片区证据，对区分同名道路没有信息量；
# 与其他词连写时照常匹配（Dubai Marina、Riyadh Park）
CITY_WORDS = {"AE": ["DUBAI", "دبي"], "SA": ["RIYADH", "الرياض"], "DE": ["BERLIN"], "FR": ["PARIS"],
              "NL": ["AMSTERDAM"], "ID": ["JAKARTA"], "TH": ["BANGKOK", "กรุงเทพมหานคร", "กรุงเทพฯ", "กรุงเทพ"],
              "VN": ["THANH PHO HO CHI MINH", "HO CHI MINH", "SAI GON"]}


def region_words(market: str) -> list[str]:
    return REGION_WORDS.get(market) or list(MARKETS[market].region_words) if market in MARKETS else []


def city_words(market: str) -> list[str]:
    return CITY_WORDS.get(market) or list(MARKETS[market].city_words) if market in MARKETS else []


@dataclass
class Span:
    text: str  # 规范化后的文字
    start: int  # 词位置
    end: int
    ids: list[int]  # 参考库对象编号
    score: float  # 100 = 完全一致
    how: str  # exact / core / fuzzy / crf


@dataclass
class Parsed:
    raw: str
    tokens: list[str]
    postcode: str | None = None
    number: str | None = None
    unit: str | None = None
    streets: list[Span] = field(default_factory=list)
    areas: list[Span] = field(default_factory=list)
    buildings: list[Span] = field(default_factory=list)
    codes: dict[str, str] = field(default_factory=dict)
    noise: dict[str, list[str]] = field(default_factory=dict)
    numbers: list[tuple[int, str]] = field(default_factory=list)  # 未被占用的数字（位置, 值）
    parser: str = "rules"
    leftover: list[str] = field(default_factory=list)


def strip_noise(raw: str, ref: MarketReference | None = None) -> tuple[str, dict[str, list[str]], dict[str, str]]:
    """非地址内容（电话、收件人、公司名、备注、营业时间、方位描述……）剥出来单独返回，见 noise.py。"""
    return _strip_noise(raw, ref)


class RuleParser:
    name = "rules"

    def __init__(self, ref: MarketReference):
        self.ref = ref
        self.m = MARKETS[ref.market]
        self.pc_re = re.compile(self.m.postcode) if self.m.postcode else None
        self._thai = ref.market == "TH"
        # 国家 / 大区 / 全城名的匹配键：容错检索时也不当片区
        self.neutral = {key(x, ref.market) for x in region_words(ref.market) + city_words(ref.market)}
        self.omit_type = self.m.omit_type  # 常省略 Jalan / Đường / شارع / ulica / tänav 的市场
        self.type_after = self.m.type_after  # 英文写法：类型词在名称后面（King Street）
        # 菲律宾商户地址常见"路名 门牌"且不写 St（Kapiligan 84, Quezon City）：段首名称紧跟门牌号时允许省略类型词
        #（开发集上本地小模型读对、规则漏掉的主要写法）
        self.street_number_order = ref.market == "PH"
        self._arabic = bool(getattr(ref, "street_skel", None))  # 阿拉伯文市场：拉丁转写 <-> 阿拉伯文
        if self._thai:
            self.nospace = {}
            for k, v in ref.street_keys.items():
                self.nospace.setdefault(k.replace(" ", ""), set()).update(v)
        self.core_fuzzy = core_fuzzy(ref)
        self.suffix = street_suffixes(ref) if ref.market in SUFFIX_MARKETS else {}
        self.stems = possessive_stems(ref) if ref.market in STEM_MARKETS else {}

    # ------------------------------------------------------------------ 主流程
    def parse(self, raw: str) -> Parsed:
        text, noise, codes = strip_noise(raw, self.ref)
        text = fold(text)  # 统一写法后再找邮编、切词（日文町丁目、西里尔文转写都在这一步）
        if self.ref.market == "SA":  # 沙特国家地址短码：4 个字母 + 4 位楼号（RCTB4359）
            m = re.search(r"\b(?!SHOP|UNIT|ROOM|FLAT|SUIT|BLOK|TOWR|GATE|EXIT)([A-Z]{4})\s?(\d{4})\b", fold(text))
            if m:
                codes["short_address"] = m.group(1) + m.group(2)
        if self.ref.market == "PR":  # 州道编号：PR-25 / Road PR 167 = Carretera 25 / 167（5 位数的 PR 00909 是邮编，不动）
            text = re.sub(r"\bPR[- ]?(\d{1,4}[A-Z]?)\b(?!\d)", r"CARRETERA \1", text)
        if self.ref.market == "CO":  # Carrera 24-30 = Carrera 24 # 30-…（漏了 #，后面的是交叉街编号）
            text = _CO_TRUNC.sub(r"\1 \2 # \3", text)
        text, postcode = self._postcode(text)
        toks = tokenize(text, self.ref.market)
        seps = tokenize_seps(text, self.ref.market)
        seps = seps if len(seps) == len(toks) else [False] * len(toks)
        if self.ref.market == "JP":
            self._japan_no_chome(toks, seps)
        p = Parsed(raw=raw, tokens=toks, postcode=postcode, codes=codes, noise=noise)
        used = [False] * len(toks)
        self._units(p, used)
        exp = [" ".join(key(t, self.ref.market).split()) or t for t in toks]
        self._regions(exp, used, seps)
        if self.ref.market == "AE":
            self._po_box_chunks(p, exp, used, seps)
        self._match(p, exp, used, "street", seps)
        self._match(p, exp, used, "area", seps)
        if self._thai:
            self._thai_nospace(p, exp)
        if self._arabic:
            weak = [sp for sp in p.streets if sp.how in ("core", "partial") and sp.end - sp.start <= 1]
            if p.streets and len(weak) == len(p.streets):
                # 只匹配上一个词（Prince Ahmad Bin Abdulaziz St -> "Ahmad"）：放开这些词，看转写能否匹配上更长的名称
                saved = p.streets
                for sp in weak:
                    used[sp.start:sp.end] = [False] * (sp.end - sp.start)
                p.streets = []
                self._translit(p, used, seps, "street")
                if not p.streets or max(sp.end - sp.start for sp in p.streets) < 2:
                    for sp in p.streets:
                        used[sp.start:sp.end] = [False] * (sp.end - sp.start)
                    p.streets = saved
                    for sp in saved:
                        used[sp.start:sp.end] = [True] * (sp.end - sp.start)
            self._translit(p, used, seps, "street")
            self._translit(p, used, seps, "area")
        if not p.streets:
            self._fuzzy(p, text, "street")
        self._fuzzy(p, text, "area")  # 已认出城市名（Dubai）时，仍要找拼写不同的片区名（Al Riqa ≈ Al Rigga）
        self._buildings(p, text)
        self._landmarks(p)
        self._number(p, exp, used)
        p.leftover = [t for t, u in zip(toks, used) if not u]
        if not self.ref.has_addresses:
            self._partial(p, exp, used, seps)
        return p

    def _translit(self, p: Parsed, used: list[bool], seps: list[bool], kind: str) -> None:
        """英文转写与阿拉伯文名称互查（Ibn Taymiyyah St. -> شارع ابن تيمية），按辅音骨架精确匹配。"""
        if (p.streets if kind == "street" else p.areas):
            return
        table = self.ref.street_skel if kind == "street" else self.ref.area_skel
        toks, n = p.tokens, len(p.tokens)
        for size in range(min(6, n), 0, -1):
            for i in range(n - size + 1):
                if any(used[i:i + size]) or any(seps[i + 1:i + size]):
                    continue
                if set(toks[i:i + size]) & (GENERIC_WORDS | UNIT_WORDS):
                    continue
                sk = skeleton(" ".join(toks[i:i + size]))
                ids = table.get(sk)
                # 骨架越短越容易撞车：单个词至少 5 个辅音（片区 4 个），多个词至少 4 个
                need = (5 if kind == "street" else 4) if size == 1 else 4
                if ids and len(sk) >= need and len(ids) <= 30:
                    span = Span(sk, i, i + size, sorted(ids), 90.0, "translit")
                    (p.streets if kind == "street" else p.areas).append(span)
                    for j in range(i, i + size):
                        used[j] = True

    def _po_box_chunks(self, p: Parsed, exp: list[str], used: list[bool], seps: list[bool]) -> None:
        """阿联酋没有邮编：除第一段外，只有数字（和城市 / 国家名）的一段是邮政信箱号，不当门牌。"""
        starts = [i for i, s in enumerate(seps) if s] + [len(exp)]
        for a, b in zip(starts[1:], starts[2:] + [len(exp)] if len(starts) > 1 else []):
            idx = range(a, b)
            if b > a and all(used[j] or exp[j].isdigit() or exp[j] in self.neutral for j in idx) \
                    and any(exp[j].isdigit() for j in idx):
                for j in idx:
                    if exp[j].isdigit() and not used[j] and 3 <= len(exp[j]) <= 7:
                        p.noise.setdefault("poBoxes", []).append(exp[j])
                        used[j] = True

    def _regions(self, exp: list[str], used: list[bool], seps: list[bool]) -> None:
        n = len(exp)
        for phrase in region_words(self.ref.market):
            words = key(phrase, self.ref.market).split()
            for i in range(n - len(words) + 1):
                if exp[i:i + len(words)] == words:
                    for j in range(i, i + len(words)):
                        used[j] = True
        for phrase in city_words(self.ref.market):
            words = key(phrase, self.ref.market).split()
            for i in range(n - len(words) + 1):
                e = i + len(words)
                if exp[i:e] == words and (i == 0 or seps[i]) and (e == n or seps[e] or all(used[e:])):
                    for j in range(i, e):
                        used[j] = True

    def _partial(self, p: Parsed, exp: list[str], used: list[bool], seps: list[bool]) -> None:
        """道路名后面紧跟着没认出来的词（Jalan Puah Jaya 只匹配上 Jalan Puah）：可能是另一条路，降为部分匹配。"""
        for sp in p.streets:
            if sp.how not in ("exact", "core") or sp.start < 0 or sp.end >= len(exp):
                continue
            nxt = exp[sp.end]
            if not used[sp.end] and not seps[sp.end] and nxt.isalpha() and len(nxt) >= 3 \
                    and not _has_type_word(nxt, self.ref.market):
                sp.how = "partial"

    # ------------------------------------------------------------------ 各组件
    def _postcode(self, text: str) -> tuple[str, str | None]:
        """text 已经过 fold。"""
        if not self.pc_re:
            return text, None
        market, rule = self.ref.market, self.m.pc_rule
        district = None
        if market == "IE":  # 都柏林邮区：Dublin 8 / Dublin 6W / 段末单独的 8 -> D08（不是门牌号）
            m = re.search(r"\bDUBLIN\s+(\d{1,2})(W?)\b|(?:^|,)\s*D?(\d{1,2})(W?)\s*$", text)
            if m:
                num, w = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
                district = f"D{int(num):02d}" if not w else f"D{int(num)}W"
                text = text[:m.start()] + (" DUBLIN " if m.group(1) else " ") + text[m.end():]
        hits = list(self.pc_re.finditer(text))
        if not hits and district:
            return text, district
        if not hits:
            return text, None
        known = [h for h in hits if norm_postcode(h.group(0), market) in self.ref.postcodes] if rule else []
        if known:  # 参考库里有的邮编优先（与门牌同为 4 位数的市场）
            hits = known[-1:]
        elif market == "AU" or rule == "end":  # 4 位邮编和门牌易混：只认州缩写后面、或整段末尾的 4 位数
            hits = [h for h in hits if re.search(r"(?:" + "|".join(AU_STATES) + r")\W*$", text[:h.start()])
                    or not text[h.end():].strip(" ,.")]
        elif rule == "chunk":  # 欧洲写法（1070 Wien）：不认识的 4 位数只有单独成段时才当邮编，否则多半是门牌
            hits = [h for h in hits if not text[:h.start()].strip() or re.search(r"[,;\n|]\s*$", text[:h.start()])]
        if not hits:
            return text, None
        h = hits[-1]
        pc = norm_postcode(h.group(0), market)
        if not pc.strip("0"):  # 00000：线上表单的占位邮编（阿联酋没有邮编）
            return text[:h.start()] + " " + text[h.end():], None
        text = text[:h.start()] + " " + text[h.end():]
        # 同一个邮编写了两遍（"47400 Petaling Jaya, 47400"、"L-1337 Luxembourg, 1337"）：都去掉，免得被当成门牌
        text = re.sub(rf"(?<![\w/-]){re.escape(h.group(0))}(?![\w/-])", " ", text)
        if pc.isdigit() and pc != h.group(0):
            text = re.sub(rf"(?<![\w/-]){re.escape(pc)}(?![\w/-])", " ", text)
        return text, pc

    def _units(self, p: Parsed, used: list[bool]) -> None:
        toks = p.tokens
        for i, t in enumerate(toks):
            if used[i]:
                continue
            if t in ("FLOOR", "FLR", "FL", "LEVEL") and i > 0 and re.fullmatch(r"\d{1,3}(?:ST|ND|RD|TH)|G|GROUND",
                                                                               toks[i - 1]):
                p.unit = p.unit or f"{toks[i - 1]} FLOOR"  # 2nd Floor, 109 Jalan …：楼层在前，后面的数字是门牌
                used[i - 1] = used[i] = True
            elif not self.ref.has_addresses and FLOOR_TOKEN.match(t) and (t != "G" or i + 1 < len(toks)
                                                                         and toks[i + 1] in ("F", "FLOOR")):
                p.unit = p.unit or f"FLOOR {t}"
                used[i] = True
            elif t in UNIT_WORDS and i + 1 < len(toks) and re.match(r"^[A-Z]?\d", toks[i + 1]):
                m = re.fullmatch(r"([A-Z]?\d+[A-Z]?)/(\d+[A-Z]?)", toks[i + 1])
                if m:  # Unit 2/45 Lyons Rd：斜杠前是单元号，斜杠后是门牌
                    p.unit = f"{t} {m.group(1)}"
                    toks[i + 1] = m.group(2)
                    used[i] = True
                    continue
                p.unit = f"{t} {toks[i + 1]}"
                used[i] = used[i + 1] = True
            elif t == "#" and i + 1 < len(toks) and not self.m.hash_number:  # 拉美的 # 标门牌，不是单元
                p.unit = "#" + toks[i + 1]
                used[i] = used[i + 1] = True
            elif re.fullmatch(r"(?:RT|RW)", t) and i + 1 < len(toks):  # 印尼 RT/RW：片区级信息，不作门牌
                used[i] = used[i + 1] = True
            elif t in MARKER_WORDS:  # No. / Kav. / KM 等门牌标记词本身不参与道路匹配（参考库里有叫 "Jalan N:O" 的路）
                used[i] = True
        # 澳洲 5/12 Smith St：斜杠前是单元号
        if self.ref.market == "AU":
            for i, t in enumerate(toks):
                m = re.fullmatch(r"(\d+[A-Z]?)/(\d+[A-Z]?)", t)
                if m and not used[i]:
                    p.unit = p.unit or f"UNIT {m.group(1)}"
                    toks[i] = m.group(2)

    def _match(self, p: Parsed, exp: list[str], used: list[bool], kind: str, seps: list[bool]) -> None:
        """最长匹配：从长到短扫描连续的词，完整键或核心键在参考库里即命中。"""
        table = self.ref.street_keys if kind == "street" else self.ref.area_keys
        core_table = self.ref.street_core if kind == "street" else self.ref.area_core
        n = len(exp)
        spans: list[Span] = []
        taken = [False] * n
        for size in range(min(7, n), 0, -1):
            for i in range(0, n - size + 1):
                if any(taken[i:i + size]) or any(used[i:i + size]) or any(seps[i + 1:i + size]):
                    continue  # 名称不会跨过逗号
                words = merge_initials(" ".join(exp[i:i + size]))
                if self.ref.market in ("IE", "BG"):
                    words = " ".join(phrase_norm(words.split(), self.ref.market))
                min_len = 2 if _CJK_RE.match(words) else (5 if kind == "street" else 4)  # 日文町名 2–3 个字（円山町）
                if kind == "street" and size == 1 and 3 <= len(words) < min_len and words.isalpha() \
                        and self._number_next(exp, Span(words, i, i + 1, [], 0, "")):
                    min_len = 3  # 短路名紧跟门牌号（塔林 Jõe 5、Aia 10a）
                if size == 1 and (len(words) < min_len or words.isdigit()):
                    continue
                if words in self.neutral:
                    continue  # 全城名 / 国家名单独出现时不是片区证据（Dubai Marina 这类更长的名称仍会匹配）
                how = None
                if words in table:
                    how = "exact"
                elif (kind == "area" or self.omit_type or _has_type_word(words, self.ref.market)
                      or (kind == "street" and self.street_number_order and (i == 0 or seps[i])
                          and i + size < n and HOUSE_NO.match(exp[i + size]))) \
                        and not (kind == "street" and self.type_after and exp[i] in TYPE_WORDS["EN"]):
                    # （英文写法类型词在名称后面：STREET GLEN IRIS 里的 STREET 属于前一条路，不能拿来匹配 Glen Iris Road）
                    # 核心键（去掉类型词）匹配：只在"习惯省略类型词"的市场，或写了类型词但写法不同时使用，
                    # 避免把片区名（Mosman）当成同名道路（Mosman Street）
                    ck = core_key(words, self.ref.market, "area" if kind == "area" else "street")
                    # 核心键同时是片区名（Jakarta、Menteng）时不当道路：多半是在写片区
                    if ck in core_table and len(ck) >= 4 and not ck.isdigit() and ck not in self.neutral and not (
                            kind == "street" and (ck in self.ref.area_keys or ck in self.ref.area_core)
                            and not _has_type_word(words, self.ref.market)
                            and not self._number_next(exp, Span(ck, i, i + size, [], 0, ""))):
                        how, words = "core", ck
                        spans.append(Span(words, i, i + size, sorted(core_table[words]), 97.0, how))
                        for j in range(i, i + size):
                            taken[j] = True
                        continue
                if how is None and kind == "street" and self.suffix and size <= 6:
                    # 人名道路的简称 / 全称：Freire = Capitán General Ramón Freire、Via Rossini = Via Gioachino Rossini、
                    # VIA GENERALE GUSTAVO FARA = Via Gustavo Fara（拉美、伊比利亚、意大利、波兰）
                    ck = core_key(words, self.ref.market)
                    # 去掉名字的首字母（K. Kärberi、F.D. Roosevelt 合并成的 FD、Jesús T. Piñero 的 T）
                    toks_c = [t for t in ck.split() if t.isdigit() or (len(t) > 1 and not (
                        len(t) <= 3 and t.isalpha() and not re.search(r"[AEIOUY]", t)))]
                    ck = " ".join(toks_c) or ck
                    ids = None
                    if ck in self.suffix and len(toks_c) <= 2:
                        ids = self.suffix[ck]
                    elif len(toks_c) >= 3 and " ".join(toks_c[-2:]) in self.ref.street_core:
                        ids = self.ref.street_core[" ".join(toks_c[-2:])]
                    elif 0 < len(toks_c) <= 2 and all(t.isalpha() for t in toks_c) and len(toks_c[-1]) >= 4 \
                            and len(words.split()) > len(toks_c) + (
                            1 if _has_type_word(words, self.ref.market) else 0):
                        # 去掉了首字母才对不上（Avenida FD Roosevelt = Avenida Franklin Delano Roosevelt）：按姓找，类型词要相容
                        ids = {x for x in last_names(self.ref).get(toks_c[-1], ()) if self._types_compatible(words, x)}
                    if ids and len(ids) <= 40:
                        spans.append(Span(ck, i, i + size, sorted(ids), 95.0, "suffix"))
                        for j in range(i, i + size):
                            taken[j] = True
                        continue
                if how is None and kind == "street" and self.stems and size <= 4 and (
                        _has_type_word(words, self.ref.market) or self._number_next(exp, Span(words, i, i + size, [], 0, ""))):
                    # 斯拉夫语人名道路的两种写法：Heinzelova / Ulica Vjekoslava Heinzela、Iblerov trg / Trg Drage Iblera
                    ids = self._stem_match(words)
                    if ids:
                        spans.append(Span(words, i, i + size, ids, 95.0, "suffix"))
                        for j in range(i, i + size):
                            taken[j] = True
                        continue
                if how:
                    spans.append(Span(words, i, i + size, sorted(table[words]), 100.0 if how == "exact" else 97.0,
                                      how))
                    for j in range(i, i + size):
                        taken[j] = True
                    # 常省略类型词的市场：输入 "Chihuahua 222" 完全对上一条叫 Chihuahua 的路，城市另一头的
                    # Calle Chihuahua 去掉类型词后也一致，同样放进候选，由门牌 / 邮编 / 片区裁决
                    # （类型词要相容：ул. Опълченска 也找名为 Опълченска 的路，但不找 бул. Опълченска）
                    # 写了类型词的市场同样处理冠词差异（Av. Manuel Maia = Avenida Manuel da Maia，而地址表的
                    # AV MANUEL MAIA 恰好对上城市另一头的同名路）：类型词相容的同核心道路也进候选
                    typed = not self.omit_type and _has_type_word(words, self.ref.market)
                    if kind == "street" and (self.omit_type or typed) and size <= 5:
                        ck = core_key(words, self.ref.market)
                        extra = [x for x in set(core_table.get(ck, ())) - set(table[words])
                                 if self._types_compatible(words, x)] if len(ck) >= 4 and not ck.isdigit() else []
                        if extra and len(extra) <= (10 if typed else 40):
                            spans.append(Span(ck, i, i + size, sorted(extra), 97.0, "core"))
                    if kind == "street" and self.suffix and size <= 6:
                        # 人名道路的全称 / 简称也进候选（Via Dante = Via Dante Alighieri、Via Giovan Battista Pergolesi =
                        # Via Giovanni Battista Pergolesi）：完全一致的同名路在别的区时，由邮编 / 片区裁决
                        ck = core_key(words, self.ref.market)
                        toks_c = ck.split()
                        if 1 <= len(toks_c) <= 4 and all(t.isalpha() for t in toks_c) and len(toks_c[-1]) >= 5:
                            pool = set(last_names(self.ref).get(toks_c[-1], ()))
                            if len(toks_c) == 1:
                                pool |= first_names(self.ref).get(toks_c[0], set())
                            else:  # 反过来：Av. Manuel Belgrano = Avenida Belgrano（路网只写姓）
                                pool |= set(self.ref.street_core.get(toks_c[-1], ()))
                            have = {x for sp in spans if sp.start == i and sp.end == i + size for x in sp.ids}
                            alt = [x for x in pool - have if self._types_compatible(words, x)
                                   and self._covers(toks_c, x)]
                            if alt and len(alt) <= 10:
                                spans.append(Span(ck, i, i + size, sorted(alt), 95.0, "alias"))
        if kind == "street":
            spans = [s for s in spans if not _all_type_words(s.text, self.ref.market)]
            # 既是道路名又是片区名（Jakarta Timur、Sydney）且没写类型词：当片区处理
            # （冠词不算类型词：La Florida 是圣地亚哥的区）
            area_like = [s for s in spans if (s.text in self.ref.area_keys
                                              or " ".join(exp[s.start:s.end]) in self.ref.area_keys)
                         and self.ref.market != "JP"
                         and not (set(exp[s.start:s.end]) & (type_words(self.ref.market) - _ARTICLES))
                         and not self._number_next(exp, s)]
            # （日本的"町丁目"既是地址表里的道路，也是片区，按道路处理）
            spans = [s for s in spans if s not in area_like]
            p.streets = sorted(spans, key=lambda s: -(s.end - s.start))
        else:
            p.areas = spans
        for s in spans:
            for j in range(s.start, s.end):
                used[j] = True

    def _japan_no_chome(self, toks: list[str], seps: list[bool]) -> None:
        """日文规范化把"町名 + 数字-数字"一律读成"町名 N 丁目 番地"；没有丁目的町（円山町 15-14、宇田川町 33-13）
        参考库里只有"町名"，这时改回"町名 + 番地 15-14"。"""
        i = 0
        while i + 2 < len(toks):
            if toks[i + 2] == "CHOME" and toks[i + 1].isdigit():
                town = key(toks[i], self.ref.market)
                chome = f"{town} {toks[i + 1]} CHOME"
                if chome not in self.ref.street_keys and town in self.ref.street_keys:
                    rest = toks[i + 3] if i + 3 < len(toks) and HOUSE_NO.match(toks[i + 3]) else ""
                    end = i + 4 if rest else i + 3
                    toks[i + 1:end] = [f"{toks[i + 1]}-{rest}" if rest else toks[i + 1]]
                    seps[i + 1:end] = [seps[i + 1]]
            i += 1

    def _covers(self, toks: list[str], sid: int) -> bool:
        """输入路名的每个词都出现在候选路名里（或互为前缀：GIOVAN / GIOVANNI）：Pedro Nunes 不能对上 Jacinto Nunes。"""
        types = type_words(self.ref.market)
        for nm in self.ref.streets[sid].names[:4]:
            theirs = [t for t in key(nm, self.ref.market).split() if t not in types]
            def match(a: str, b: str) -> bool:
                return a == b or (min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)))
            if theirs and (all(any(match(c, t) for c in theirs) for t in toks)
                           or all(any(match(c, t) for t in toks) for c in theirs)):
                return True
        return False

    def _stem_match(self, words: str) -> list[int]:
        types = type_words(self.ref.market)
        toks = [t for t in words.split() if t not in types]
        if not toks or not all(t.isalpha() for t in toks) or words in self.neutral:
            return []  # 门牌号不能并进路名（25 Panónska cesta）
        mine = set(words.split()) & types
        ids = [sid for sid, theirs in self.stems.get(possessive_stem(toks[-1]), ())
               if not mine or not theirs or mine <= theirs or theirs <= mine]
        return sorted(set(ids)) if 0 < len(set(ids)) <= 10 else []

    def _types_compatible(self, words: str, sid: int) -> bool:
        from .text import MARKET_LANG
        types = type_words(self.ref.market) - _ARTICLES
        mine = set(words.split()) & types
        if not mine:
            return True
        for nm in self.ref.streets[sid].names:
            k = key(nm, self.ref.market)
            if re.fullmatch(r"[A-Z]{1,3}-?\d+[A-Z]?", k.replace(" ", "")):
                continue  # 道路编号（B517、N11）本身没有类型词，不能当"类型相容"的依据
            theirs = set(k.split()) & types
            if not theirs or mine <= theirs or theirs <= mine:
                return True
        return False

    def _number_next(self, exp: list[str], s: Span) -> bool:
        """名称紧挨着门牌号（Mlynské nivy 5501、12 Smith St）：是道路，不是同名片区。"""
        j = s.end if not self.m.number_first else s.start - 1
        return 0 <= j < len(exp) and bool(HOUSE_NO.match(exp[j])) and exp[j].strip("0") != ""

    def _thai_nospace(self, p: Parsed, exp: list[str]) -> None:
        """泰文分词可能与参考库不一致：去掉空格后按子串再找一遍道路。"""
        if p.streets:
            return
        joined = "".join(exp)
        best = None
        for i in range(len(joined)):
            for j in range(len(joined), i + 3, -1):
                sub = joined[i:j]
                if sub in self.nospace and (best is None or len(sub) > len(best[0])):
                    best = (sub, sorted(self.nospace[sub]))
                    break
        if best and len(best[0]) >= 5:
            p.streets.append(Span(best[0], 0, 0, best[1], 95.0, "thai"))

    def _fuzzy(self, p: Parsed, text: str, kind: str) -> None:
        """按逗号 / 换行切段，每段去掉数字和单元词后做容错检索。"""
        index = self.ref.street_fuzzy if kind == "street" else self.ref.area_fuzzy
        if index is None:
            return
        out: list[Span] = []
        street_words = {w for s in p.streets for w in s.text.split()} if kind == "area" else set()
        for seg in re.split(r"[,\n;|]+|\s-\s", text):
            if street_words and street_words & set(key(seg, self.ref.market).split()):
                continue  # 已识别为道路的片段，不再当片区找
            words = [w for w in key(seg, self.ref.market).split()
                     if not HOUSE_NO.match(w) and w not in UNIT_WORDS and w not in NUMBER_MARKERS]
            if " ".join(words) in self.neutral or "".join(words) in {x.replace(" ", "") for x in self.neutral}:
                continue
            for cand in {" ".join(words), core_key(" ".join(words), self.ref.market,
                                                    "area" if kind == "area" else "street")}:
                if len(cand) < 5:
                    continue
                hits = index.search(cand, limit=3, min_score=86)
                if kind == "street" and self.core_fuzzy is not None:  # 去掉类型词后再比（Tsarigradsko Shosse ≈ бул. Цариградско шосе）
                    hits += [h for h in self.core_fuzzy.search(cand, limit=3, min_score=88) if h[1] < 100]
                for k, score, ids in hits:
                    if kind == "street" and k in self.ref.area_keys:
                        continue  # 与片区同名的道路（Dubai Marina）：当片区
                    if re.findall(r"\d+", k) != re.findall(r"\d+", cand):
                        continue  # 数字不做容错（Calle 69 不是 Calle 68，荒川 6 丁目不是 5 丁目）
                    out.append(Span(k, -1, -1, ids, score, "fuzzy"))
        out.sort(key=lambda s: -s.score)
        if kind == "street":
            p.streets = out[:4]
        else:
            seen = {a for s in p.areas for a in s.ids}
            p.areas += [s for s in out[:4] if not set(s.ids) <= seen]

    def _landmarks(self, p: Parsed) -> None:
        """方位描述里的参照物（third house behind Café Central、frente al Mercado San Miguel）：只找楼宇 / 商户，
        不匹配道路；找到的楼宇在引擎里带 LANDMARK_RELATIVE，最多 CONFIRM。冠词可能属于名称（Der Landstreicher），两种都试。"""
        if self.ref.poi_fuzzy is None:
            return
        from .noise import LEADING_ARTICLE
        for phrase in p.noise.get("landmarks", []):
            k = " ".join(w for w in key(phrase, self.ref.market).split() if not HOUSE_NO.match(w))
            for cand in dict.fromkeys((k, LEADING_ARTICLE.sub("", k))):
                if self._landmark(p, cand):
                    break

    def _landmark(self, p: Parsed, cand: str) -> bool:
        if len(cand) < 5 or len(cand.split()) > 8 or cand in self.neutral or generic_name(cand):
            return False
        found = False
        for hit, score, ids in self.ref.poi_fuzzy.search(cand, limit=2, min_score=90):  # 楼宇类：容错
            if len(ids) <= 20 and not generic_name(hit):
                p.buildings.append(Span(hit, -1, -1, ids, score, "exact" if score == 100 else "fuzzy"))
                found = True
        ids = all_poi_names(self.ref).get(cand, []) if not found else []  # 任何商户：名称完全一致才算
        if 0 < len(ids) <= 20:
            p.buildings.append(Span(cand, -1, -1, ids, 100.0, "exact"))
            found = True
        return found

    def _buildings(self, p: Parsed, text: str) -> None:
        if self.ref.poi_fuzzy is None:
            return
        taken = {s.text for s in p.streets + p.areas}
        for seg in re.split(r"[,\n;|]+|\s-\s", text):
            k = key(seg, self.ref.market)
            inside = [sp for sp in p.streets if sp.text and sp.text in k and sp.how != "exact"]
            if any(t and t in k for t in taken) and not (inside and BUILDING_WORDS.search(seg)):
                continue  # 已认成道路 / 片区的片段（但 "Mall of Emirates" 这种带楼宇词的片段仍要找楼名）
            words = [w for w in k.split() if not HOUSE_NO.match(w)]
            cand = " ".join(words)
            if len(cand) < 6 or len(words) > 8 or all(w in GENERIC_WORDS or w in UNIT_WORDS for w in words):
                continue
            if cand in self.neutral:  # 只写了城市名（Bratislava）：不能纠错成同名的商户 / 机构（Bratislava I.）
                continue
            found = False
            for hit, score, ids in self.ref.poi_fuzzy.search(cand, limit=2, min_score=90):
                if len(ids) <= 20 and not generic_name(hit):
                    p.buildings.append(Span(hit, -1, -1, ids, score, "exact" if score == 100 else "fuzzy"))
                    found = True
            if found:  # 楼名里的词被当成了道路（Mall of Emirates -> Emirates Street）：去掉这些道路候选
                p.streets = [sp for sp in p.streets if sp not in inside]
            if not found and hasattr(self.ref.poi_fuzzy, "pos"):  # 片段里嵌着楼名：Riyadh Park-inside Debenhams
                for size in range(min(5, len(words) - 1), 1, -1):
                    hits = [(" ".join(words[i:i + size]), self.ref.poi_fuzzy.get(" ".join(words[i:i + size])))
                            for i in range(len(words) - size + 1)]
                    hits = [(h, ids) for h, ids in hits if ids and len(ids) <= 20 and len(h) >= 8
                            and not generic_name(h)]
                    if hits:
                        p.buildings += [Span(h, -1, -1, ids, 100.0, "exact") for h, ids in hits]
                        break

    def _number(self, p: Parsed, exp: list[str], used: list[bool]) -> None:
        pcs = self.ref.postcodes
        cand: list[tuple[int, str]] = [(i, t) for i, t in enumerate(p.tokens)
                                       if not used[i] and HOUSE_NO.match(t) and t.strip("0")
                                       and not (len(t) >= 5 and t in pcs)]  # 5 位数且是已知邮编：多半是邮编
        p.numbers = cand
        if not cand:
            return
        street = next((s for s in p.streets if s.start >= 0), None)
        if street is not None:
            before = [c for c in cand if c[0] < street.start]
            after = [c for c in cand if c[0] >= street.end]
            first = (max(before)[1] if before else None, min(after)[1] if after else None)
            if self.m.number_first:
                p.number = first[0] or first[1]
            else:
                p.number = first[1] or first[0]
        else:
            # 数字前面有 No. / # / رقم 等标记的优先
            marked = [c for c in cand if c[0] > 0 and p.tokens[c[0] - 1] in NUMBER_MARKERS]
            p.number = (marked or cand)[0][1]
        for i, t in cand:
            if t == p.number:
                used[i] = True
                # 哥伦比亚 "# 75 35" = 75-35（交叉街编号 + 距离），中间漏了连字符
                if self.ref.market == "CO" and re.fullmatch(r"\d{1,3}[A-Z]?", t) and i + 1 < len(p.tokens) \
                        and not used[i + 1] and re.fullmatch(r"\d{1,3}", p.tokens[i + 1]):
                    p.number = f"{t}-{p.tokens[i + 1]}"
                    used[i + 1] = True
                break
        if self.ref.market == "NL" and p.number:  # 荷兰：35hs、162A、283-30 = 门牌 + 附加（官方表里记在单元里）
            m = re.fullmatch(r"(\d+)(?:(HS|BG|BV|[A-Z])|-(\w+))", p.number)
            if m:
                p.number, p.unit = m.group(1), p.unit or (m.group(2) or m.group(3))


_CO_TRUNC = re.compile(r"\b(CALLE|CARRERA|CRA|KR|CL|CLL|AK|AC|TRANSVERSAL|TV|DIAGONAL|DG)\.?\s+(\d{1,3}[A-Z]?)"
                       r"\s*-\s*(\d{1,3}[A-Z]?)\b(?!\s*-)")
_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
_ARTICLES = {"DE", "DEL", "LA", "LAS", "LOS", "EL", "DA", "DO", "DAS", "DOS", "DI", "D", "DU", "L", "DES", "LE",
             "DELLA", "DEI", "DEGLI", "DELLE", "DELLO", "E"}
# 人名道路常用简称的市场（Capitán General Ramón Freire -> Freire、Avenida Doctor Tristán Achával Rodríguez -> Achával Rodríguez）
SUFFIX_MARKETS = {"AR", "MX", "CL", "CO", "PR", "ES", "BR", "PT", "IT", "PL", "EE", "LV", "LT"}


# 斯拉夫语：人名道路有"物主形容词"和"名 + 姓（属格）"两种写法（Gajeva ulica = Ulica Ljudevita Gaja、Štúrova = Ulica
# Ľudovíta Štúra、Čapkova = Karla Čapka），两者去掉词尾后的词干相同
STEM_MARKETS = {"HR", "SI", "SK", "CZ"}
_POSS_ENDINGS = ("OVA", "EVA", "OVO", "EVO", "INA", "OV", "EV", "IN", "A", "E")


def possessive_stem(tok: str) -> str:
    for suf in _POSS_ENDINGS:
        if tok.endswith(suf) and len(tok) - len(suf) >= 3:
            tok = tok[:-len(suf)]
            break
    # 词尾的"游移 e"：Basariček -> Basaričeka / Basarička、Sadovec -> Sadovca，统一去掉
    return re.sub(r"(?<=[A-Z]{2})E([BCDFGHJKLMNPRSTVZ])$", r"\1", tok)


def possessive_stems(ref: MarketReference) -> dict[str, list[tuple[int, frozenset]]]:
    """词干 -> [(道路, 道路名里的类型词)]：取去掉类型词后最后一个词（≥ 4 个字母）的词干。"""
    out = ref.__dict__.get("_stems")
    if out is not None:
        return out
    out = {}
    types = type_words(ref.market)
    for s in ref.streets:
        for nm in s.names[:4]:
            k = key(nm, ref.market)
            toks = [t for t in k.split() if t not in types]
            if not toks or not toks[-1].isalpha() or len(toks[-1]) < 4:
                continue
            out.setdefault(possessive_stem(toks[-1]), []).append((s.id, frozenset(set(k.split()) & types)))
    ref.__dict__["_stems"] = out
    return out


def core_fuzzy(ref: MarketReference):
    """去掉类型词后的路名容错索引（加载时建一次，按参考库缓存）。"""
    from .fuzzy import FuzzyIndex
    idx = ref.__dict__.get("_core_fuzzy")
    if idx is None:
        idx = ref.__dict__["_core_fuzzy"] = FuzzyIndex({k: sorted(v) for k, v in ref.street_core.items() if len(k) >= 5})
    return idx


def first_names(ref: MarketReference) -> dict[str, set[int]]:
    """去掉类型词后正好 2 个词的路名：第一个词 -> 道路（Via Dante Alighieri 常简写作 Via Dante）。"""
    out = ref.__dict__.get("_first_names")
    if out is None:
        out = {}
        types = type_words(ref.market)
        for k, ids in ref.street_core.items():
            toks = [t for t in k.split() if t not in types]
            if len(toks) == 2 and toks[0].isalpha() and len(toks[0]) >= 5 and toks[1].isalpha():
                out.setdefault(toks[0], set()).update(ids)
        ref.__dict__["_first_names"] = out
    return out


def last_names(ref: MarketReference) -> dict[str, set[int]]:
    """去掉类型词后至少 2 个词的路名：最后一个词 -> 道路（不排除与别的路名重名的，用时再按类型词筛）。"""
    out = ref.__dict__.get("_last_names")
    if out is None:
        out = {}
        types = type_words(ref.market)
        for k, ids in ref.street_core.items():
            toks = [t for t in k.split() if t not in types]
            if len(toks) >= 2 and toks[-1].isalpha() and len(toks[-1]) >= 4:  # 4 个字母的姓只在写了首字母时用（A. Čaka）
                out.setdefault(toks[-1], set()).update(ids)
        ref.__dict__["_last_names"] = out
    return out


def street_suffixes(ref: MarketReference) -> dict[str, set[int]]:
    """人名道路的简称：去掉类型词后至少 2 个词的名称取最后 1 个词（≥ 5 个字母），至少 3 个词的再取最后 2 个词。"""
    out = ref.__dict__.get("_suffix")
    if out is not None:
        return out
    out = {}
    lang_types = type_words(ref.market)
    for k, ids in ref.street_core.items():
        toks = [t for t in k.split() if t not in lang_types]
        if len(toks) < 2 or not toks[-1].isalpha():
            continue
        for suf in ([toks[-1]] if len(toks[-1]) >= 5 else []) + ([" ".join(toks[-2:])] if len(toks) >= 3 else []):
            if suf in ref.street_keys or suf in ref.street_core or suf in ref.area_keys:
                continue
            out.setdefault(suf, set()).update(ids)
    ref.__dict__["_suffix"] = out
    return out


def all_poi_names(ref: MarketReference) -> dict[str, list[int]]:
    """全部商户的名称 -> 编号（不只楼宇类）：只给方位描述里的参照物用（"第三栋，在 Londis 后面"），用到时才生成。"""
    out = ref.__dict__.get("_poi_all")
    if out is None:
        out = {}
        for pid, name in ref.db.execute("SELECT id, name FROM poi"):
            k = key(name or "", ref.market)
            if len(k) >= 5:
                out.setdefault(k, []).append(pid)
        ref.__dict__["_poi_all"] = out
    return out


def generic_name(name: str) -> bool:
    """只由通用词和编号组成的楼名（Building 9、Tower A4、Business Center）：不能当楼名证据。"""
    return all(w in GENERIC_WORDS or w in UNIT_WORDS or w.isdigit() or len(w) == 1
               or (len(w) <= 3 and any(ch.isdigit() for ch in w)) for w in name.split())  # A4、B2 这类编号


def tokenize_seps(text: str, market: str | None = None) -> list[bool]:
    """每个词前面是否有逗号 / 分号 / 换行（与 tokenize(text) 的词一一对应）。"""
    seps: list[bool] = []
    for chunk in re.split(r"[,;\n|،]+", text):
        n = len(tokenize(chunk, market))
        seps += [True] + [False] * (n - 1) if n else []
    return seps


def _has_type_word(text: str, market: str) -> bool:
    from .text import TYPE_WORDS, MARKET_LANG
    return bool(set(text.split()) & type_words(market))


# 最初的 11 个市场：只由类型词 + 数字组成的名称（JALAN 3）不当道路名；其他市场的编号道路是正常路名
#（哥伦比亚 Carrera 14、墨西哥 Calle 5、日本 丸の内 2 CHOME）
_DIGIT_IS_TYPE = {"AU", "DE", "FR", "NL", "AE", "SA", "MY", "ID", "TH", "VN", "PH"}


def _all_type_words(text: str, market: str) -> bool:
    from .text import TYPE_WORDS, MARKET_LANG
    words = text.split()
    tw = type_words(market) | TYPE_WORDS["AREA"]
    return all(w in tw or (w.isdigit() and market in _DIGIT_IS_TYPE) for w in words)


def describe_script(text: str) -> str:
    return script_of(text)
