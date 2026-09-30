"""按各市场的真实写法，把参考库里的道路 / 片区 / 楼宇 / 地址点渲染成地址文字，并给每个词打上标签。

两个用途：
  1. 构造合成测试集（已知标准答案）
  2. 生成机器学习解析器（CRF）的训练数据（与 libpostal 的做法相同：用结构化地址按各国格式渲染出训练样本）
训练和测试按道路名哈希分开（训练 70% / 测试 30%），测试集里的道路名不会出现在训练数据里。

标签：NUM 门牌、UNIT 单元 / 楼层、STREET 道路、BLDG 楼宇 / POI、AREA 片区、CITY 城市、PC 邮编、O 其他
"""

from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass

from .reference import MarketReference

CITY = {"AU": ["Sydney", "Melbourne"], "DE": ["Berlin"], "FR": ["Paris"], "NL": ["Amsterdam"],
        "AE": ["Dubai", "دبي", "Dubai, UAE"], "SA": ["Riyadh", "الرياض", "Riyadh, Saudi Arabia"],
        "MY": ["Kuala Lumpur", "KL", "Wilayah Persekutuan Kuala Lumpur", "Petaling Jaya, Selangor"],
        "ID": ["Jakarta", "Jakarta Selatan", "Jakarta Pusat", "DKI Jakarta"],
        "TH": ["Bangkok", "กรุงเทพฯ", "กรุงเทพมหานคร"], "VN": ["TP.HCM", "Hồ Chí Minh", "TP. Hồ Chí Minh", "Sài Gòn"],
        "PH": ["Manila", "Metro Manila", "Makati City", "Quezon City"]}
UNIT_FMT = {"AU": ["Unit {u}", "Level {f}", "Suite {u}", "Shop {u}"], "DE": ["{f}. OG", "Whg. {u}"],
            "FR": ["Bât. {b}", "Apt {u}", "{f}e étage"], "NL": [], "AE": ["Office {u}", "Flat {u}", "Apt {u}",
                                                                      "Floor {f}", "Villa {u}"],
            "SA": ["Office {u}", "الطابق {f}", "Floor {f}"], "MY": ["Unit {f}-{u}", "Lot {u}", "Level {f}"],
            "ID": ["Lantai {f}", "Unit {u}", "Blok {b} No. {u}"], "TH": ["ชั้น {f}", "Floor {f}", "Room {u}"],
            "VN": ["Tầng {f}", "Phòng {u}"], "PH": ["Unit {u}", "Floor {f}", "Rm {u}"]}
AU_STATE = {"Sydney": "NSW", "Melbourne": "VIC"}
# 道路类型词的缩写写法（渲染时随机采用）
STREET_ABBR = {"STREET": ["St", "St."], "ROAD": ["Rd", "Rd."], "AVENUE": ["Ave", "Av"], "DRIVE": ["Dr"],
               "HIGHWAY": ["Hwy"], "PARADE": ["Pde"], "CRESCENT": ["Cres"], "PLACE": ["Pl"], "LANE": ["Ln"],
               "STRASSE": ["Str."], "RUE": ["r."], "BOULEVARD": ["Bd", "Blvd"], "JALAN": ["Jl.", "Jln", "Jln."],
               "DUONG": ["Đ.", "Đường"], "THANON": ["ถ."], "SOI": ["ซ."], "LORONG": ["Lrg", "Lor."],
               "PERSIARAN": ["Psn"], "GANG": ["Gg."]}


@dataclass
class Sample:
    text: str
    tokens: list[str]
    labels: list[str]
    truth: dict  # 标准答案：street / point / building / area / 坐标
    seps: list[bool] = None  # 每个词前面是否有逗号等分隔符（CRF 特征）


def street_split(name: str) -> str:
    """按道路名哈希：train（70%）/ test（30%）。"""
    h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16) % 10
    return "train" if h < 7 else "test"


def _typo(word: str, rng: random.Random) -> str:
    letters = [i for i, c in enumerate(word) if c.isalpha()]
    if len(letters) < 4:
        return word
    i = rng.choice(letters[1:])
    op = rng.choice(["del", "sub", "swap", "dup"])
    if op == "del":
        return word[:i] + word[i + 1:]
    if op == "sub":
        return word[:i] + rng.choice("aeiounrstl") + word[i + 1:]
    if op == "swap" and i + 1 < len(word):
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    return word[:i] + word[i] + word[i:]


def _abbrev(name: str, rng: random.Random, p: float) -> str:
    out = []
    for w in name.split():
        up = re.sub(r"[^\w]", "", w.upper()).replace("ĐƯỜNG", "DUONG").replace("STRAßE", "STRASSE")
        if up in STREET_ABBR and rng.random() < p:
            out.append(rng.choice(STREET_ABBR[up]))
        elif up.endswith("STRASSE") and len(up) > 8 and rng.random() < p:
            out.append(w[: len(w) - 6] + "str.")
        else:
            out.append(w)
    return " ".join(out)


class Renderer:
    def __init__(self, ref: MarketReference, split: str, seed: int = 0):
        self.ref = ref
        self.market = ref.market
        self.rng = random.Random(seed)
        self.split = split
        self.street_ids = [s.id for s in ref.streets if street_split(s.name) == split and len(s.name) >= 4]
        self.area_names = {a.id: a for a in ref.areas}

    # ------------------------------------------------------------------ 组件
    def _street_name(self, s) -> str:
        names = s.names
        if self.market in ("AE", "SA", "TH") and len(names) > 1 and self.rng.random() < 0.5:
            name = self.rng.choice(names[1:])  # 英文 / 其他语种写法
        else:
            name = names[0]
        return name

    def _areas(self, s) -> tuple[str | None, str | None]:
        subs = [self.ref.areas[a] for a in s.areas]
        small = [a for a in subs if a.subtype in ("neighborhood", "microhood", "macrohood")]
        big = [a for a in subs if a.subtype in ("locality", "county", "localadmin", "borough")]
        pick = lambda xs: (self.rng.choice(self.rng.choice(xs).names[:2]) if xs else None)  # noqa: E731
        return pick(small), pick(big)

    def _building_near(self, s) -> str | None:
        if not s.points:
            return None
        lat, lng = self.rng.choice(s.points)
        rows = self.ref.db.execute(
            "SELECT name FROM poi WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ? AND "
            "(category LIKE '%building%' OR category LIKE '%mall%' OR category LIKE '%hotel%' OR category LIKE "
            "'%apartment%' OR category LIKE '%tower%' OR category LIKE '%office%' OR category LIKE '%plaza%') LIMIT 5",
            (lat - 0.0015, lat + 0.0015, lng - 0.0015, lng + 0.0015)).fetchall()
        return self.rng.choice(rows)[0] if rows else None

    def _number(self) -> str:
        r = self.rng.random()
        n = str(int(self.rng.expovariate(1 / 60)) + 1)
        if self.market in ("VN", "TH") and r < 0.35:
            return f"{n}/{self.rng.randint(1, 60)}"
        if r < 0.1:
            return n + self.rng.choice("ABC")
        return n

    # ------------------------------------------------------------------ 样本
    def sample(self, noise: float = 0.3) -> Sample | None:
        rng, ref = self.rng, self.ref
        if ref.has_addresses:
            return self._sample_point(noise)
        s = ref.streets[rng.choice(self.street_ids)]
        area, district = self._areas(s)
        if not area and not district and rng.random() < 0.7:
            return None
        parts: dict[str, str | None] = {
            "street": _abbrev(self._street_name(s), rng, 0.4),
            "number": self._number() if rng.random() < 0.8 else None,
            "area": area if rng.random() < 0.85 else None,
            "district": district if rng.random() < 0.5 else None,
            "building": self._building_near(s) if rng.random() < 0.25 else None,
            "unit": None, "postcode": None, "city": rng.choice(CITY[self.market]) if rng.random() < 0.7 else None,
        }
        if rng.random() < 0.2 and UNIT_FMT.get(self.market):
            parts["unit"] = rng.choice(UNIT_FMT[self.market]).format(u=rng.randint(1, 40), f=rng.randint(1, 30),
                                                                     b=rng.choice("ABCD"))
        if self.market not in ("AE",) and rng.random() < 0.5:
            pcs = [pc for pc, (a, b, n) in ref.postcodes.items()
                   if abs(a - s.lat) < 0.01 and abs(b - s.lng) < 0.01 and n >= 5]
            parts["postcode"] = rng.choice(pcs) if pcs else None
        truth = {"street": s.id, "lat": s.lat, "lng": s.lng, "number": parts["number"]}
        return self._compose(parts, truth, noise)

    def _sample_point(self, noise: float) -> Sample | None:
        rng, ref = self.rng, self.ref
        for _ in range(20):
            sid = rng.choice(self.street_ids)
            pts = ref.addresses([sid])
            if pts:
                break
        else:
            return None
        pt = rng.choice(pts)
        s = ref.streets[sid]
        city = rng.choice(CITY[self.market])
        parts = {"street": _abbrev(s.name.title() if s.name.isupper() else s.name, rng, 0.6),
                 "number": pt["number"] if rng.random() > 0.05 else None,
                 "area": pt["locality"].title() if pt["locality"] and rng.random() < 0.7 else None,
                 "district": None, "building": None,
                 "unit": (pt["unit"].title() if pt["unit"] else None) if rng.random() < 0.8 else None,
                 "postcode": pt["postcode"] if rng.random() > 0.08 else None,
                 "city": city if rng.random() < 0.3 else None}
        if self.market == "AU" and parts["postcode"]:
            parts["postcode"] = f"{AU_STATE.get(city, 'NSW')} {parts['postcode']}" if rng.random() < 0.6 \
                else parts["postcode"]
        truth = {"street": sid, "point": pt["id"], "lat": pt["lat"], "lng": pt["lng"], "number": pt["number"]}
        return self._compose(parts, truth, noise)

    def _compose(self, parts: dict, truth: dict, noise: float) -> Sample:
        """按市场语序拼接，逐段打标签；再按比例加噪声（错拼、大小写、漏逗号）。"""
        rng, m = self.rng, self.market
        seq: list[tuple[str, str]] = []  # (文字, 标签)
        num, st = parts["number"], parts["street"]
        if rng.random() < noise * 0.3:
            words = st.split()
            j = rng.randrange(len(words))
            words[j] = _typo(words[j], rng)
            st = " ".join(words)
            truth["typo"] = True
        if parts["building"]:
            seq.append((parts["building"], "BLDG"))
        if parts["unit"]:
            seq.append((parts["unit"], "UNIT"))
        if m in ("DE", "NL"):
            seq.append((st, "STREET"))
            if num:
                seq.append((num, "NUM"))
        elif m == "ID":
            seq.append((st, "STREET"))
            if num:
                seq += [("No.", "O"), (num, "NUM")]
            if rng.random() < 0.4:
                seq.append((f"RT.{rng.randint(1, 15)}/RW.{rng.randint(1, 12)}", "AREA"))
        elif m == "AU" and num and parts["unit"] and parts["unit"].startswith("Unit") and rng.random() < 0.6:
            u = parts["unit"].split()[-1]
            seq = [x for x in seq if x[1] != "UNIT"] + [(f"{u}/", "UNIT"), (num, "NUM"), (st, "STREET")]
        else:
            if num:
                prefix = rng.choice(["", "", "No. "]) if m in ("MY", "PH") else ("Building " if m == "SA" and
                                                                                rng.random() < 0.3 else "")
                if prefix:
                    seq.append((prefix.strip(), "O"))
                seq.append((num, "NUM"))
            seq.append((st, "STREET"))
        for k, lab in (("area", "AREA"), ("district", "AREA")):
            if parts[k]:
                word = ""
                if m == "VN" and rng.random() < 0.5:
                    word = rng.choice(["P.", "Phường "]) if k == "area" else rng.choice(["Q.", "Quận "])
                seq.append((word + parts[k], lab))
        if m in ("DE", "FR", "NL") and parts["postcode"]:
            seq.append((parts["postcode"], "PC"))
            seq.append((parts["city"] or CITY[m][0], "CITY"))
        else:
            if parts["city"]:
                seq.append((parts["city"], "CITY"))
            if parts["postcode"]:
                seq.append((parts["postcode"], "PC"))
        # 组装文字与逐词标签（分隔符：逗号为主，偶尔省略）
        from .crf import tokenize_with_sep
        text_parts, tokens, labels, seps = [], [], [], []
        for i, (txt, lab) in enumerate(seq):
            prev = seq[i - 1] if i else ("", "")
            if i == 0 or prev[0].endswith("/"):
                sep = ""
            elif {prev[1], lab} == {"NUM", "STREET"} or (lab == "NUM" and prev[1] == "O") or prev[1] == "O":
                sep = " " if rng.random() < 0.92 else ", "  # 门牌和道路之间通常不加逗号
            else:
                sep = ", " if rng.random() < 0.8 else " "
            text_parts.append(sep + txt)
            toks, sp = tokenize_with_sep(txt)
            if sp:
                sp[0] = i == 0 or sep == ", "
            tokens += toks
            seps += sp
            labels += [lab] * len(toks)
        text = "".join(text_parts)
        r = rng.random()
        if r < noise * 0.3:
            text = text.lower()
        elif r < noise * 0.45:
            text = text.upper()
        truth["text_parts"] = {k: v for k, v in parts.items() if v}
        return Sample(text, tokens, labels, truth, seps)
