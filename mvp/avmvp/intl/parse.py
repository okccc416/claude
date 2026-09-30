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
from .reference import MarketReference
from .text import TYPE_WORDS, core_key, fold, key, merge_initials, script_of, skeleton, tokenize

PHONE = re.compile(r"(?:\+|00)\d{1,3}[\s\-]?\(?\d{1,4}\)?(?:[\s\-]?\d{2,4}){2,4}|(?<![\d/])0\d{8,10}(?![\d/])|"
                   r"(?<![\d/])[89]\d{3}\s?\d{4}(?![\d/])")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
URL = re.compile(r"https?://\S+|www\.\S+")
PLUS_CODE = re.compile(r"\b[23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3}\b", re.I)
MAKANI = re.compile(r"(?<!\d)\d{5}\s\d{5}(?!\d)")
UNIT_WORDS = {"UNIT", "APARTMENT", "SUITE", "SHOP", "FLAT", "LEVEL", "FLOOR", "LANTAI", "TANG", "ชั้น", "ห้อง",
              "الطابق", "شقه", "مكتب", "LOT", "ROOM", "KIOSK", "STALL", "OFFICE", "TOWER", "BLOCK", "BLOK"}
NUMBER_MARKERS = {"NO", "NOMOR", "NUMBER", "BLK", "#", "رقم", "مبني", "SỐ", "SO", "เลขที่"}
HOUSE_NO = re.compile(r"^\d{1,5}[A-Z]?(?:[/\-]\d{1,5}[A-Z]?){0,2}$")
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


def strip_noise(raw: str) -> tuple[str, dict[str, list[str]], dict[str, str]]:
    noise: dict[str, list[str]] = {}
    codes: dict[str, str] = {}
    text = raw
    for name, rx in (("urls", URL), ("emails", EMAIL)):
        found = rx.findall(text)
        if found:
            noise[name] = found
            text = rx.sub(" ", text)
    for name, rx in (("plus_code", PLUS_CODE), ("makani", MAKANI)):
        m = rx.search(text)
        if m:
            codes[name] = m.group(0).upper()
            text = text[:m.start()] + " " + text[m.end():]
    phones = PHONE.findall(text)
    if phones:
        noise["phones"] = [p.strip() for p in phones]
        text = PHONE.sub(" ", text)
    return text, noise, codes


class RuleParser:
    name = "rules"

    def __init__(self, ref: MarketReference):
        self.ref = ref
        self.m = MARKETS[ref.market]
        self.pc_re = re.compile(self.m.postcode) if self.m.postcode else None
        self._thai = ref.market == "TH"
        self.omit_type = ref.market in ("MY", "ID", "VN", "TH", "AE", "SA")  # 这些市场常省略 Jalan / Đường / شارع
        self.type_after = ref.market in ("AU", "PH", "AE", "SA")  # 英文写法：类型词在名称后面（King Street）
        self._arabic = bool(getattr(ref, "street_skel", None))  # 阿拉伯文市场：拉丁转写 <-> 阿拉伯文
        if self._thai:
            self.nospace = {}
            for k, v in ref.street_keys.items():
                self.nospace.setdefault(k.replace(" ", ""), set()).update(v)

    # ------------------------------------------------------------------ 主流程
    def parse(self, raw: str) -> Parsed:
        text, noise, codes = strip_noise(raw)
        if self.ref.market == "SA":  # 沙特国家地址短码：4 个字母 + 4 位楼号（RCTB4359）
            m = re.search(r"\b(?!SHOP|UNIT|ROOM|FLAT|SUIT|BLOK|TOWR|GATE|EXIT)([A-Z]{4})\s?(\d{4})\b", fold(text))
            if m:
                codes["short_address"] = m.group(1) + m.group(2)
        text, postcode = self._postcode(text)
        toks = tokenize(text)
        p = Parsed(raw=raw, tokens=toks, postcode=postcode, codes=codes, noise=noise)
        used = [False] * len(toks)
        self._units(p, used)
        exp = [" ".join(key(t, self.ref.market).split()) or t for t in toks]
        seps = tokenize_seps(text)
        seps = seps if len(seps) == len(exp) else [False] * len(exp)
        self._regions(exp, used, seps)
        self._match(p, exp, used, "street", seps)
        self._match(p, exp, used, "area", seps)
        if self._thai:
            self._thai_nospace(p, exp)
        if self._arabic:
            self._translit(p, used, seps, "street")
            self._translit(p, used, seps, "area")
        if not p.streets:
            self._fuzzy(p, text, "street")
        self._fuzzy(p, text, "area")  # 已认出城市名（Dubai）时，仍要找拼写不同的片区名（Al Riqa ≈ Al Rigga）
        self._buildings(p, text)
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
                sk = skeleton(" ".join(toks[i:i + size]))
                ids = table.get(sk)
                if ids and len(sk) >= (4 if kind == "street" else 3) and len(ids) <= 30:
                    span = Span(sk, i, i + size, sorted(ids), 90.0, "translit")
                    (p.streets if kind == "street" else p.areas).append(span)
                    for j in range(i, i + size):
                        used[j] = True

    def _regions(self, exp: list[str], used: list[bool], seps: list[bool]) -> None:
        n = len(exp)
        for phrase in REGION_WORDS.get(self.ref.market, []):
            words = key(phrase, self.ref.market).split()
            for i in range(n - len(words) + 1):
                if exp[i:i + len(words)] == words:
                    for j in range(i, i + len(words)):
                        used[j] = True
        for phrase in CITY_WORDS.get(self.ref.market, []):
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
        if not self.pc_re:
            return text, None
        up = fold(text)
        hits = list(self.pc_re.finditer(up))
        if not hits:
            return text, None
        if self.ref.market == "AU":  # 澳洲 4 位邮编和门牌易混：只认州缩写后面、或整段末尾的 4 位数
            hits = [h for h in hits if re.search(r"(?:" + "|".join(AU_STATES) + r")\W*$", up[:h.start()])
                    or not up[h.end():].strip(" ,.")]
        if not hits:
            return text, None
        h = hits[-1]
        pc = h.group(0).replace(" ", "")
        if not pc.strip("0"):  # 00000：线上表单的占位邮编（阿联酋没有邮编）
            return text[:h.start()] + " " + text[h.end():], None
        text = text[:h.start()] + " " + text[h.end():]
        # 同一个邮编写了两遍（"47400 Petaling Jaya, 47400"）：都去掉，免得被当成门牌
        return re.sub(rf"(?<![\w/-]){re.escape(h.group(0))}(?![\w/-])", " ", text), pc

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
            elif t == "#" and i + 1 < len(toks):
                p.unit = "#" + toks[i + 1]
                used[i] = used[i + 1] = True
            elif re.fullmatch(r"(?:RT|RW)", t) and i + 1 < len(toks):  # 印尼 RT/RW：片区级信息，不作门牌
                used[i] = used[i + 1] = True
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
                if size == 1 and (len(words) < (5 if kind == "street" else 4) or words.isdigit()):
                    continue
                how = None
                if words in table:
                    how = "exact"
                elif (kind == "area" or self.omit_type or _has_type_word(words, self.ref.market)) \
                        and not (kind == "street" and self.type_after and exp[i] in TYPE_WORDS["EN"]):
                    # （英文写法类型词在名称后面：STREET GLEN IRIS 里的 STREET 属于前一条路，不能拿来匹配 Glen Iris Road）
                    # 核心键（去掉类型词）匹配：只在"习惯省略类型词"的市场，或写了类型词但写法不同时使用，
                    # 避免把片区名（Mosman）当成同名道路（Mosman Street）
                    ck = core_key(words, self.ref.market, "area" if kind == "area" else "street")
                    # 核心键同时是片区名（Jakarta、Menteng）时不当道路：多半是在写片区
                    if ck in core_table and len(ck) >= 4 and not ck.isdigit() and not (
                            kind == "street" and ck in self.ref.area_keys and not _has_type_word(words, self.ref.market)):
                        how, words = "core", ck
                        spans.append(Span(words, i, i + size, sorted(core_table[words]), 97.0, how))
                        for j in range(i, i + size):
                            taken[j] = True
                        continue
                if how:
                    spans.append(Span(words, i, i + size, sorted(table[words]), 100.0 if how == "exact" else 97.0,
                                      how))
                    for j in range(i, i + size):
                        taken[j] = True
        if kind == "street":
            spans = [s for s in spans if not _all_type_words(s.text, self.ref.market)]
            # 既是道路名又是片区名（Jakarta Timur、Sydney）且没写类型词：当片区处理
            area_like = [s for s in spans if s.text in self.ref.area_keys
                         and not _has_type_word(" ".join(exp[s.start:s.end]), self.ref.market)]
            spans = [s for s in spans if s not in area_like]
            p.streets = sorted(spans, key=lambda s: -(s.end - s.start))
        else:
            p.areas = spans
        for s in spans:
            for j in range(s.start, s.end):
                used[j] = True

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
            for cand in {" ".join(words), core_key(" ".join(words), self.ref.market,
                                                    "area" if kind == "area" else "street")}:
                if len(cand) < 5:
                    continue
                for k, score, ids in index.search(cand, limit=3, min_score=86):
                    out.append(Span(k, -1, -1, ids, score, "fuzzy"))
        out.sort(key=lambda s: -s.score)
        if kind == "street":
            p.streets = out[:4]
        else:
            seen = {a for s in p.areas for a in s.ids}
            p.areas += [s for s in out[:4] if not set(s.ids) <= seen]

    def _buildings(self, p: Parsed, text: str) -> None:
        if self.ref.poi_fuzzy is None:
            return
        taken = {s.text for s in p.streets + p.areas}
        for seg in re.split(r"[,\n;|]+|\s-\s", text):
            k = key(seg, self.ref.market)
            if any(t and t in k for t in taken):
                continue  # 已认成道路 / 片区的片段
            words = [w for w in k.split() if not HOUSE_NO.match(w)]
            cand = " ".join(words)
            if len(cand) < 6 or len(words) > 8:
                continue
            found = False
            for hit, score, ids in self.ref.poi_fuzzy.search(cand, limit=2, min_score=90):
                if len(ids) <= 20:
                    p.buildings.append(Span(hit, -1, -1, ids, score, "exact" if score == 100 else "fuzzy"))
                    found = True
            if not found and hasattr(self.ref.poi_fuzzy, "pos"):  # 片段里嵌着楼名：Riyadh Park-inside Debenhams
                for size in range(min(5, len(words) - 1), 1, -1):
                    hits = [(" ".join(words[i:i + size]), self.ref.poi_fuzzy.get(" ".join(words[i:i + size])))
                            for i in range(len(words) - size + 1)]
                    hits = [(h, ids) for h, ids in hits if ids and len(ids) <= 20 and len(h) >= 8]
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
                break


def tokenize_seps(text: str) -> list[bool]:
    """每个词前面是否有逗号 / 分号 / 换行（与 tokenize(text) 的词一一对应）。"""
    seps: list[bool] = []
    for chunk in re.split(r"[,;\n|،]+", text):
        n = len(tokenize(chunk))
        seps += [True] + [False] * (n - 1) if n else []
    return seps


def _has_type_word(text: str, market: str) -> bool:
    from .text import TYPE_WORDS, MARKET_LANG
    return bool(set(text.split()) & TYPE_WORDS.get(MARKET_LANG.get(market, "EN"), set()))


def _all_type_words(text: str, market: str) -> bool:
    from .text import TYPE_WORDS, MARKET_LANG
    words = text.split()
    tw = TYPE_WORDS.get(MARKET_LANG.get(market, "EN"), set()) | TYPE_WORDS["AREA"]
    return all(w in tw or w.isdigit() for w in words)


def describe_script(text: str) -> str:
    return script_of(text)
