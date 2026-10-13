"""全国门址库（试点城市以外）：一个国家全部的官方地址点（scripts/fetch_national.py 生成的 national.sqlite），
按门牌号召回、按路名和城镇 / 邮编核对。

试点城市的参考库装在内存里、只覆盖试点城市；试点以外的地址原来只能给到城镇级（范围守卫）。真实流量里约一半的
失败落在试点城市以外，而这些地址大多就在国家的官方地址表里，所以这里只用门牌点、不用路网：
  召回  门牌号相同，且（邮编相同 / 城镇名在原文里 / 路名第一个核心词的前 3 个字母相同——容忍错拼）
  核对  路名：geo_text.route_match（各语言类型词、缩写、拼写容错，与 geo 核对层同一套）
        城镇 / 邮编：邮编相同、城镇名整词出现在原文里，或与原文某个词组只差一两个字母（Mosgeil = Mosgiel）
  结论  路名完全一致、门牌一致、邮编或城镇印证、全国只有这一处 -> ACCEPT；拼写纠正 / 城镇只是近似 / 有别处同名同号
        -> CONFIRM（列出候选）；门牌查不到但路名在所写城镇里 -> 道路级 CONFIRM
"""

from __future__ import annotations

import re
import sqlite3
import threading
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from .coverage import norm
from .geo_text import PARTICLES, TYPES, UNIT_WORDS, route_match, street_part
from .noise import strip_noise
from .reference import DATA, haversine, number_key
from .text import fold, norm_postcode

CLUSTER_M = 150.0  # 同一处地址的多个点（多个入口、单元）
SCHEMA = """
CREATE TABLE addr(id INTEGER PRIMARY KEY, street TEXT, s3 TEXT, number TEXT, nkey TEXT, unit TEXT, postcode TEXT,
                  locality TEXT, lkey TEXT, region TEXT, lat REAL, lng REAL);
"""
# s3 = 路名第一个核心词（去掉类型词、冠词）的前 3 个字母：容错检索的入口（Liverpol St 与 Liverpool Street 都是 LIV）
INDEXES = ["CREATE INDEX addr_n_s3 ON addr(nkey, s3)", "CREATE INDEX addr_s3_pc ON addr(s3, postcode)",
           "CREATE INDEX addr_s3_l ON addr(s3, lkey)"]


def name_prefix(street: str) -> str:
    """路名第一个核心词（去掉类型词、冠词、单元词）的前 3 个字母；编号道路（Calle 72、Street 7）取 #编号。"""
    words = norm(street).split()
    for w in words:
        if w not in TYPES and w not in PARTICLES and w not in UNIT_WORDS and not w.isdigit() and len(w) >= 2:
            return w[:3]
    nums = [re.match(r"\d+", w).group(0) for w in words if re.match(r"\d+", w)]
    return f"#{nums[0]}" if nums else ""


@dataclass
class NationalMatch:
    street: str
    number: str
    postcode: str
    locality: str
    lat: float
    lng: float
    street_level: str  # CONFIRMED / CORRECTED
    place: str  # postcode / locality / locality_fuzzy / ""
    premise: bool
    ambiguous: bool = False
    others: list[dict] = field(default_factory=list)  # 别处的同名同号（候选）


class NationalIndex:
    def __init__(self, cc: str, directory=None):
        self.cc = cc
        path = (directory or DATA / cc) / "national.sqlite"
        self.db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False) if path.exists() else None
        self.lock = threading.Lock()

    def _rows(self, sql: str, args: list) -> list[tuple]:
        with self.lock:
            return self.db.execute(sql, args).fetchall()

    def lookup(self, text: str, number: str | None, postcode: str | None, pc_re=None) -> NationalMatch | None:
        if self.db is None:
            return None
        clean = strip_noise(text)[0]
        _, name, _ = street_part(clean, pc_re)
        prefixes = sorted({w[:3] for w in name if len(w) >= 3 and w not in TYPES and w not in PARTICLES
                           and w not in UNIT_WORDS and not re.search(r"\d", w)}
                          | {"#" + re.match(r"\d+", w).group(0) for w in name if re.match(r"\d+[A-Z]?$", w)})
        words = norm(pc_re.sub(" ", fold(clean)) if pc_re else clean).split()
        grams = {" ".join(words[i:i + n]) for n in (1, 2, 3) for i in range(len(words) - n + 1)}
        grams = {g for g in grams if len(g) >= 3 and not g.isdigit()}
        pc = norm_postcode(postcode, self.cc) if postcode else ""
        if not prefixes and not pc:
            return None
        cols = "street, number, postcode, locality, lkey, lat, lng"
        rows: list[tuple] = []
        if number:
            nums = _number_variants(number)
            qn = ",".join("?" * len(nums))
            if prefixes:
                rows += self._rows(f"SELECT {cols} FROM addr WHERE nkey IN ({qn}) AND s3 IN ({','.join('?' * len(prefixes))})",
                                   nums + prefixes)
            if pc:
                rows += self._rows(f"SELECT {cols} FROM addr WHERE nkey IN ({qn}) AND postcode=?", nums + [pc])
        hit = self._best(rows, clean, pc_re, pc, grams, premise=True)
        if hit is not None or not prefixes:
            return hit
        # 门牌查不到：路名在所写城镇 / 邮编里 -> 道路级
        qp = ",".join("?" * len(prefixes))
        street_rows = []
        if pc:
            street_rows += self._rows(f"SELECT {cols} FROM addr WHERE s3 IN ({qp}) AND postcode=? LIMIT 3000",
                                      prefixes + [pc])
        towns = [g for g in grams if len(g) >= 4][:60]
        if towns:
            street_rows += self._rows(f"SELECT {cols} FROM addr WHERE s3 IN ({qp}) AND lkey IN "
                                      f"({','.join('?' * len(towns))}) LIMIT 3000", prefixes + towns)
        return self._best(street_rows, clean, pc_re, pc, grams, premise=False)

    def _best(self, rows: list[tuple], clean: str, pc_re, pc: str, grams: set[str], premise: bool):
        seen = {}
        for street, num, rpc, loc, lkey, lat, lng in rows:
            seen[(street, num, rpc, loc, round(lat, 5), round(lng, 5))] = (street, num, rpc, loc, lkey, lat, lng)
        scored = []
        route_cache: dict[str, str] = {}
        for street, num, rpc, loc, lkey, lat, lng in seen.values():
            sl = route_cache.get(street)
            if sl is None:
                sl = route_cache[street] = route_match(street, clean, pc_re)
            if sl not in ("CONFIRMED", "CORRECTED"):
                continue
            if pc and rpc == pc:
                place = "postcode"
            elif lkey and lkey in grams:
                place = "locality"
            elif lkey and len(lkey) >= 5 and any(abs(len(g) - len(lkey)) <= 2 and fuzz.ratio(g, lkey) >= 85
                                                 for g in grams):
                place = "locality_fuzzy"
            else:
                place = ""
            if not premise and not place:  # 道路级只认所写城镇 / 邮编里的路
                continue
            score = (3.0 if sl == "CONFIRMED" else 2.0) + {"postcode": 3.0, "locality": 2.5, "locality_fuzzy": 1.5,
                                                           "": 0.0}[place]
            scored.append((score, street, num, rpc, loc, lat, lng, sl, place))
        if not scored:
            return None
        scored.sort(key=lambda x: -x[0])
        best = scored[0]
        if not premise:  # 道路级：取这条路在所写城镇里各门牌点的中间一个
            same = [x for x in scored if x[1] == best[1] and x[4] == best[4]]
            same.sort(key=lambda x: (x[5], x[6]))
            best = same[len(same) // 2]
        others = [x for x in scored[1:] if haversine(x[5], x[6], best[5], best[6]) > CLUSTER_M
                  and (premise or x[1] != best[1] or x[4] != best[4])]
        ambiguous = any(x[0] >= best[0] - 0.5 for x in others)
        if premise and not best[8] and others:  # 原文没有可印证的城镇 / 邮编，全国又不止一处同名同号：不选
            ambiguous = True
        return NationalMatch(best[1], best[2] if premise else "", best[3], best[4], best[5], best[6], best[7], best[8],
                             premise, ambiguous,
                             [{"street": x[1], "number": x[2], "postcode": x[3], "area": x[4], "lat": x[5],
                               "lng": x[6], "source": "national"} for x in others[:4]])


def _number_variants(number: str) -> list[str]:
    n = number_key(number)
    out = [n]
    m = re.fullmatch(r"(\d+[A-Z]?)[-/](\d+[A-Z]?)", n)
    if m:
        out += [m.group(1), m.group(2)]
    return list(dict.fromkeys(out))


def national(ref) -> NationalIndex:
    """与参考库放在同一目录（data/markets/<国家>/national.sqlite），随参考库缓存。"""
    idx = ref.__dict__.get("_national")
    if idx is None:
        idx = ref.__dict__["_national"] = NationalIndex(ref.market, ref.dir)
    return idx
