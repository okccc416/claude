"""全国门址库（试点城市以外）：一个国家全部的官方地址点（scripts/fetch_national.py 生成的 national.sqlite），
按门牌号召回、按路名和城镇 / 邮编核对。

试点城市的参考库装在内存里、只覆盖试点城市；试点以外的地址原来只能给到城镇级（范围守卫）。真实流量里约一半的
失败落在试点城市以外，而这些地址大多就在国家的官方地址表里，所以这里只用门牌点、不用路网：
  召回  门牌号相同，且（路名第一个核心词的前 3 个字母相同——容忍后面的错拼 / 邮编相同 / 城镇名在原文里——路名开头
        拼错也能召回）
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
from functools import lru_cache

from rapidfuzz import fuzz

from .coverage import norm
from .geo_text import PARTICLES, TYPES, UNIT_WORDS, _core, numbered_only, other_words, route_match, street_part
from .noise import strip_noise
from .reference import DATA, haversine, number_key, warm_file
from .text import MARKET_ABBREV, fold, norm_postcode

CLUSTER_M = 150.0  # 同一处地址的多个点（多个入口、单元）
# 哥伦比亚式网格门牌：Calle 16 # 22-53 = 16 号 Calle 上、从 22 号 Carrera 路口往前 53 米。路名只有"类型 + 编号"，
# 类型和编号都要对上（Calle 16 不是 Carrera 16），# 后面的 22-53 是一个整体（不拆成 22、53 两个门牌）
GRID = {"CO"}
_GRID_TYPE = {"CALLE": "CL", "CLL": "CL", "CL": "CL", "AC": "CL", "CARRERA": "KR", "CRA": "KR", "CRR": "KR",
              "KRA": "KR", "KR": "KR", "CR": "KR", "AK": "KR", "TRANSVERSAL": "TV", "TRANSV": "TV", "TV": "TV",
              "TR": "TV", "DIAGONAL": "DG", "DIAG": "DG", "DG": "DG", "AVENIDA": "AV", "AVDA": "AV", "AV": "AV",
              "CIRCULAR": "CQ", "CQ": "CQ"}
_GRID_RE = re.compile(r"(?<![A-Z])(" + "|".join(sorted(_GRID_TYPE, key=len, reverse=True))
                      + r")\.?\s*(\d{1,3})(\s?)([A-Z])?(?:\s?(BIS))?(?:\s?(SUR|ESTE|NORTE|OESTE|[NSEO]))?(?![A-Z])")
_PLATE_RE = re.compile(r"\s*(?:(?:SUR|ESTE|NORTE|OESTE|BIS)\b\s*)*(?:#|N[O°º]\.?|NUMERO|NRO\.?)?\s*(\d{1,3})\s?([A-Z])?"
                       r"(?:\s?(?:BIS|SUR|ESTE|NORTE|OESTE|[NSEO]))?(?![A-Z])\s*(?:#|-|\s)\s*(\d{1,3})(?!\d)")


def _grid_key(m: re.Match) -> tuple[str, str, str, str]:
    """(类型, 编号, 字母 / BIS, 方位)。Calle 9 Sur（CL 9 S）、Carrera 9 Bis 与 Calle 9、Carrera 9 是不同的路。"""
    letter, card = m.group(4) or "", (m.group(6) or "")[:1]
    if letter in ("N", "S", "E", "O") and m.group(3) and not card:  # CL 17 E、CL 9 S：分开写的单个字母是方位
        letter, card = "", letter
    return _GRID_TYPE[m.group(1)], str(int(m.group(2))), letter + (m.group(5) or ""), card


def grid_key(street: str) -> tuple[str, str, str, str] | None:
    """网格路名 -> (类型, 编号, 字母, 方位)：Calle 39a、CL 39A -> (CL, 39, A, "")；CL 9A S -> (CL, 9, A, S)。"""
    m = _GRID_RE.search(fold(street))
    return _grid_key(m) if m else None


def grid_input(text: str) -> tuple[dict, str]:
    """原文里所有网格路名 {(类型, 编号, 字母): {方位}}，和第一个路名后面的门牌（# 17 b 53 -> 17B-53）。"""
    t = fold(text)
    keys: dict[tuple, set] = {}
    plate = ""
    for m in _GRID_RE.finditer(t):
        k = _grid_key(m)
        keys.setdefault(k[:3], set()).add(k[3])
        if k[2] in ("N", "S", "E", "O") and not k[3]:  # 原文 Cl. 6N 多半是 6 Norte：两种读法都算
            keys.setdefault((k[0], k[1], ""), set()).add(k[2])
        if not plate:
            pm = _PLATE_RE.match(t, m.end())
            if pm:
                plate = number_key(f"{int(pm.group(1))}{pm.group(2) or ''}-{pm.group(3)}")
    return keys, plate


def grid_match(street: str, grid: dict) -> str | None:
    """候选路名 vs 原文的网格路名：None = 候选不是网格路名（按普通路名比）。原文没写方位、候选有（Calle 9 -> CL 9 S）
    算纠正；原文写了方位、候选不同算冲突。"""
    gk = grid_key(street)
    if gk is None:
        return None
    cards = grid.get(gk[:3])
    if cards is None:
        return "CONFLICT"
    if gk[3] in cards:
        return "CONFIRMED"
    return "CORRECTED" if "" in cards else "CONFLICT"
SCHEMA = """
CREATE TABLE addr(id INTEGER PRIMARY KEY, street TEXT, s3 TEXT, number TEXT, nkey TEXT, unit TEXT, postcode TEXT,
                  locality TEXT, lkey TEXT, region TEXT, lat REAL, lng REAL);
"""
# s3 = 路名第一个核心词（去掉类型词、冠词）的前 3 个字母：容错检索的入口（Liverpol St 与 Liverpool Street 都是 LIV）
# 召回入口：门牌 + 路名前缀 / 门牌 + 城镇（路名开头就拼错：freyer = Fryer）/ 路名前缀 + 邮编、城镇（道路级）
INDEXES = ["CREATE INDEX addr_n_s3 ON addr(nkey, s3)", "CREATE INDEX addr_n_l ON addr(nkey, lkey)",
           "CREATE INDEX addr_s3_pc ON addr(s3, postcode)", "CREATE INDEX addr_s3_l ON addr(s3, lkey)",
           "CREATE INDEX addr_n_pc ON addr(nkey, postcode)"]  # 门牌 + 邮编（没有它要扫全国同号的门牌，单条查询几百毫秒）


def locality_key(locality: str) -> str:
    """城镇名的检索键：去掉官方名称里的附加说明（Hannover, Landeshauptstadt、Oldenburg (Oldenb.), Stadt -> HANNOVER、
    OLDENBURG），用户只写城镇名本身。"""
    return norm(re.sub(r"\([^)]*\)", " ", (locality or "").split(",")[0]))


def name_prefix(street: str) -> str:
    """路名第一个核心词（去掉类型词、冠词、单元词和两个字母以下的词——Am Volksgarten 取 VOL）的前 3 个字母；
    编号道路（Calle 72、Street 7）取 #编号。与查询时原文路名的取法一致。"""
    words = norm(street).split()
    for w in words:
        if w not in TYPES and w not in PARTICLES and w not in UNIT_WORDS and not w.isdigit() and len(w) >= 3:
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
    written_postcode: str = ""  # 原文里写的邮编（解析没认出来的也算：B-4770、门牌后面紧跟的 2840）
    block: bool = False  # 网格门牌查不到，取同一条路、同一个或相邻路口的门牌（门牌附近）
    written_number: str = ""  # 按原文重拆的门牌（网格门牌 # 17 b 53 -> 17B-53）


# 澳新的州 / 领地缩写写在邮编前或段尾（3 Auber Gln NSW 2759）：不是路名的一部分
_STATE_TAIL = {"AU": re.compile(r"\b(?:NSW|VIC|QLD|TAS|WA|SA|NT|ACT)\b(?=\s*(?:\d{4})?\s*(?:[,;]|$))", re.I)}


def market_text(text: str, cc: str) -> str:
    """查全国门址库前按国家整理原文：去掉段尾的州缩写，展开该国的路类型缩写（Gln -> GLEN、Cir -> CIRCLE）。"""
    st = _STATE_TAIL.get(cc)
    if st:
        text = st.sub(" ", text)
    table = MARKET_ABBREV.get(cc) if cc in ("AU", "NZ") else None  # 哥伦比亚的 S / E / N 由网格门牌自己处理
    if table:
        text = re.sub(r"[A-Za-z]+", lambda m: table.get(m.group(0).upper(), m.group(0)), text)
    return text


class NationalIndex:
    def __init__(self, cc: str, directory=None):
        self.cc = cc
        path = (directory or DATA / cc) / "national.sqlite"
        self.db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False) if path.exists() else None
        self.lock = threading.Lock()
        self.warm_thread = None
        if self.db is not None:
            self.db.execute("PRAGMA mmap_size=4294967296")  # 只读库按内存映射读，少一次拷贝
            self.warm_thread = warm_file(path)  # 后台读进页缓存，冷启动的查询不用等读盘

    def _rows(self, sql: str, args: list) -> list[tuple]:
        with self.lock:
            return self.db.execute(sql, args).fetchall()

    def lookup(self, text: str, number: str | None, postcode: str | None, pc_re=None,
               max_others: int = 4) -> NationalMatch | None:
        if self.db is None:
            return None
        clean = market_text(strip_noise(text)[0], self.cc)
        _, name, locality = street_part(clean, pc_re)
        self_words = locality | other_words(clean, pc_re)  # 道路段以外的词（城镇名要从这里印证）
        written = _core(name)[0]
        if locality and [w for w in written if w not in locality]:
            written = [w for w in written if w not in locality]  # 与 route_match 同样去掉夹在道路段里的城镇名
        prefixes = sorted({w[:3] for w in name if len(w) >= 3 and w not in TYPES and w not in PARTICLES
                           and w not in UNIT_WORDS and not re.search(r"\d", w)}
                          | {"#" + re.match(r"\d+", w).group(0) for w in name if re.match(r"\d+[A-Z]?$", w)})
        words = norm(pc_re.sub(" ", fold(clean)) if pc_re else clean).split()
        grams = {" ".join(words[i:i + n]) for n in (1, 2, 3) for i in range(len(words) - n + 1)}
        grams = {g for g in grams if len(g) >= 3 and not g.isdigit()}
        towns = sorted((g for g in grams if len(g) >= 4), key=lambda g: (-len(g), g))[:60]  # 固定顺序，结果可复现
        # 原文里所有像邮编的串（解析层没认出的也算），解析出的邮编排第一
        pcs = list(dict.fromkeys([norm_postcode(postcode, self.cc)] if postcode else []
                                 + ([norm_postcode(m.group(0), self.cc) for m in pc_re.finditer(fold(clean))]
                                    if pc_re else [])))
        if not prefixes and not pcs:
            return None
        grid, plate = grid_input(clean) if self.cc in GRID else ({}, "")
        if plate:
            number = plate  # 网格门牌按原文重拆（解析层会把 # 17 b 53 拆成 17）
        if grid:  # 网格路名的前缀：编号（CL 16 -> #16，CL 39A -> 39A）
            prefixes = sorted({"#" + n for _, n, _ in grid} | {(n + l)[:3] for _, n, l in grid if len(n + l) >= 3})
        cols = "street, number, postcode, locality, lkey, lat, lng"
        # 道路段里除门牌以外的数字（编号道路 Calle 5 的 5）；道路段以外的词（城镇名的印证只算这些里的）
        ctx = {"street_nums": {w for w in name if re.search(r"\d", w)} - {number_key(number or "")},
               "other": self_words}
        rows: list[tuple] = []
        hit = None
        if number:
            nums = [number_key(number)] if grid else number_variants(number, self.cc)
            qn = ",".join("?" * len(nums))
            if pcs:
                rows += self._rows(f"SELECT {cols} FROM addr WHERE nkey IN ({qn}) AND postcode IN "
                                   f"({','.join('?' * len(pcs))})", nums + pcs)
            if towns:
                town_sql = f"SELECT {cols} FROM addr WHERE nkey IN ({qn}) AND lkey IN ({','.join('?' * len(towns))})"
                got = self._rows(town_sql + f" LIMIT {TOWN_ROWS}", nums + towns)
                if len(got) >= TOWN_ROWS and prefixes:  # 大城市（Madrid 同号的门牌几万个）：只留路名前缀对得上的
                    got = self._rows(town_sql + f" AND s3 IN ({','.join('?' * len(prefixes))})", nums + towns + prefixes)
                rows += got
            if rows and max_others <= 4:  # 先只看所写邮编 / 城镇里的同号门牌：邮编印证、或路名完全对上且城镇印证，
                # 又不歧义时，全国按路名前缀的召回不用再查（要列全国同名同号的调用方除外）
                hit = self._best(rows, clean, pc_re, pcs, grams, name, written, grid, premise=True, ctx=ctx,
                                 max_others=max_others)
                if hit is not None and (hit.ambiguous or not (hit.place == "postcode" or (
                        hit.place == "locality" and hit.street_level == "CONFIRMED"))):
                    hit = None
            if hit is None and prefixes:
                pre_sql = f"SELECT {cols} FROM addr WHERE nkey IN ({qn}) AND s3 IN ({','.join('?' * len(prefixes))})"
                if rows:  # 所写邮编 / 城镇在库里、那里却没对上：全国同号同前缀的路太多（Sch… 开头的德国路名两万条）时
                    # 不再全国比对（只为救"邮编 / 城镇写错"，代价是单条查询半秒以上）
                    got = self._rows(pre_sql + f" LIMIT {PREFIX_ROWS + 1}", nums + prefixes)
                    rows += got if len(got) <= PREFIX_ROWS else []
                else:
                    rows += self._rows(pre_sql, nums + prefixes)
        if hit is None:
            hit = self._best(rows, clean, pc_re, pcs, grams, name, written, grid, premise=True, ctx=ctx,
                             max_others=max_others)
        base = re.fullmatch(r"(\d+)[A-Z]", number_key(number or ""))
        if hit is None and base and not grid and prefixes:  # 45A 不在表里、45 在：取 45（门牌附近，请用户确认）
            hit = self._best(self._rows(f"SELECT {cols} FROM addr WHERE nkey=? AND s3 IN "
                                        f"({','.join('?' * len(prefixes))})", [base.group(1)] + prefixes),
                             clean, pc_re, pcs, grams, name, written, grid, premise=True, ctx=ctx)
            if hit is not None and not hit.place:
                hit = None  # 只认所写城镇 / 邮编里的
        if hit is None and plate and prefixes and (towns or pcs):
            hit = self._block(grid, plate, prefixes, cols, towns, pcs, grams)
        if hit is not None:
            hit.written_number = plate or number or ""
        if hit is not None or not prefixes:
            return hit
        # 门牌查不到：路名在所写城镇 / 邮编里 -> 道路级
        qp = ",".join("?" * len(prefixes))
        street_rows = []
        if pcs:
            street_rows += self._rows(f"SELECT {cols} FROM addr WHERE s3 IN ({qp}) AND postcode IN "
                                      f"({','.join('?' * len(pcs))}) LIMIT 3000", prefixes + pcs)
        if towns:
            street_rows += self._rows(f"SELECT {cols} FROM addr WHERE s3 IN ({qp}) AND lkey IN "
                                      f"({','.join('?' * len(towns))}) LIMIT 3000", prefixes + towns)
        return self._best(street_rows, clean, pc_re, pcs, grams, name, written, grid, premise=False, ctx=ctx)

    def _block(self, grid: dict, plate: str, prefixes: list[str], cols: str, towns: list[str], pcs: list[str],
               grams: set[str]):
        """网格门牌查不到：同一条路上、同一个路口（# 22-）的其他门牌里取距离数最接近的；这个路口没有门牌点时取相邻
        路口（# 21- / # 23-，一个街区约百米）。"""
        cross, dist = (int(re.match(r"\d+", x).group(0)) for x in plate.split("-", 1))
        place_sql = " OR ".join(x for x in (f"lkey IN ({','.join('?' * len(towns))})" if towns else "",
                                            f"postcode IN ({','.join('?' * len(pcs))})" if pcs else "") if x)
        rows = self._rows(f"SELECT {cols} FROM addr WHERE s3 IN ({','.join('?' * len(prefixes))}) AND ({place_sql}) "
                          f"LIMIT 20000", prefixes + towns + pcs)
        best = None
        for street, num, rpc, loc, lkey, lat, lng in rows:
            m = re.fullmatch(r"(\d+)[A-Z]?\s*[-\s]\s*(\d+)", num.strip().upper())  # 官方表写作 108 16
            gm = grid_match(street, grid) if m and abs(int(m.group(1)) - cross) <= 1 else None
            if gm not in ("CONFIRMED", "CORRECTED"):
                continue
            place = "postcode" if rpc and rpc in pcs else "locality" if lkey in grams else ""
            if not place:
                continue
            key = (gm != "CONFIRMED", place != "postcode", abs(int(m.group(1)) - cross), abs(int(m.group(2)) - dist))
            if best is None or key < best[0]:
                best = (key, street, num, rpc, loc, lat, lng, place)
        if best is None:
            return None
        key, street, num, rpc, loc, lat, lng, place = best
        return NationalMatch(street, "", rpc, loc, lat, lng, "CORRECTED" if key[0] else "CONFIRMED", place, False,
                             block=True,
                             written_postcode=rpc if rpc in pcs else (pcs[0] if pcs else ""))

    def _best(self, rows: list[tuple], clean: str, pc_re, pcs: list[str], grams: set[str], name: list[str],
              written: list[str], grid: dict, premise: bool, ctx: dict | None = None, max_others: int = 4):
        seen = {}
        for street, num, rpc, loc, lkey, lat, lng in rows:
            seen[(street, num, rpc, loc, round(lat, 5), round(lng, 5))] = (street, num, rpc, loc, lkey, lat, lng)
        scored = []
        route_cache: dict[str, str] = {}
        fuzzy_town: dict[str, str] = {}
        folded = fold(clean)
        name_set = set(name)
        cands = list(seen.values())
        if not grid and len({c[0] for c in cands}) > MANY_STREETS:
            # 召回的路太多（San / Santa 开头的路名，全国几万条同号）：先只留下核心词与原文核心词有两个以上对得上
            # （路名只有一个核心词的对上一个）的路，免得逐条比几万次路名（单条查询会到一秒）
            wp = {w[:3] for w in written if len(w) >= 3}
            cands = [c for c in cands if len(_street_info(c[0])[3] & wp) >= min(2, len(_street_info(c[0])[3]))]
        for street, num, rpc, loc, lkey, lat, lng in cands:
            s_words, s_core, s_nums, _, s_numbered = _street_info(street)
            # 城镇名没用逗号隔开、夹在道路段里（25 hall street pitt town 2756）：按这一处的城镇把它从原文里拿掉再比路名，
            # 免得以城镇命名的路（Pitt Street、The Ponds Boulevard）把城镇名当成路名对上
            town_in_name = bool(lkey) and not grid and set(lkey.split()) <= name_set and not set(lkey.split()) <= ctx["other"] \
                and any(w not in lkey.split() for w in written)  # 路名就是城镇名（6 Glenbrook Rd 2773）时不拿掉
            rkey = (street, lkey if town_in_name else "")
            sl = route_cache.get(rkey)
            if sl is None:
                gm = grid_match(street, grid) if self.cc in GRID else None
                if gm is not None:  # 网格路名：类型、编号、字母都要与原文的某个路名相同（原文没写出网格路名也不认）
                    sl = gm
                elif town_in_name:
                    hits = list(re.finditer(rf"\b{re.escape(lkey)}\b", folded))
                    text = folded[:hits[-1].start()] + folded[hits[-1].end():] if hits else folded
                    sl = route_match(street, text, pc_re)
                else:
                    sl = route_match(street, clean, pc_re)
                route_cache[rkey] = sl
            if sl not in ("CONFIRMED", "CORRECTED"):
                continue
            if not grid and s_numbered and not set(s_nums) <= ctx["street_nums"]:
                continue  # 编号道路（Calle Transversal 5）：编号要写在道路段里，不能是门牌号本身
            if rpc and rpc in pcs:
                place = "postcode"
            elif lkey and lkey in grams:
                place = "locality"
            elif lkey:
                place = fuzzy_town.get(lkey)
                if place is None:
                    if len(lkey) >= 5 and any(abs(len(g) - len(lkey)) <= 2 and fuzz.ratio(g, lkey) >= 85 for g in grams):
                        place = "locality_fuzzy"
                    elif any(len(g) >= 5 and lkey.startswith(g + " ") for g in grams):
                        place = "locality_fuzzy"  # 只写了正式名称的前半（Sant Cugat = Sant Cugat del Vallès）
                    else:
                        place = ""
                    fuzzy_town[lkey] = place
            else:
                place = ""
            if place.startswith("locality") and set(lkey.split()) <= set(s_words) \
                    and not set(lkey.split()) <= ctx["other"]:
                place = ""  # 城镇名只是路名的一部分（Calle Serra 印证不了 Serra 镇）
            if not place and (not premise or sl != "CONFIRMED" or grid or (rpc and pcs)):
                # 没有邮编 / 城镇印证：门牌级只认路名完全对上、且邮编不与原文冲突的（原文写的邮编在别处 = 多半是
                # 数据缺了这一处，选别的城市的同名同号是错的）；网格门牌各城市大量重复，也不认；道路级不认
                continue
            # 路名的核心词与原文完全相同（Nieuwstraat 不是 Korte Nieuwstraat，Avenue Prince de Liège 不是
            # Chaussée de Liège）加 0.6，足以分开"原文只是另一条路名的一部分"；其余同分按字面相似度排
            # （Am Volskgarten：Am Volksgarten 先于 Volksgartenstraße），加分不到 0.5，不影响歧义判断
            own = [w for w in written if w not in lkey.split()] if town_in_name else written
            exact = bool(s_core) and set(s_core) == set(own)
            sim = fuzz.token_sort_ratio(" ".join(s_words), " ".join(name)) / 100 if name else 0.0
            both = place == "postcode" and bool(lkey) and lkey in grams and (
                town_in_name or not set(lkey.split()) <= set(s_words) or set(lkey.split()) <= ctx["other"])
            score = (3.0 if sl == "CONFIRMED" else 2.0) + {"postcode": 3.0, "locality": 2.5, "locality_fuzzy": 1.5,
                                                           "": 0.0}[place] + 0.5 * both + 0.6 * exact + 0.4 * sim
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
        if best[8] == "postcode":  # 原文写的邮编就是这一处的：别处邮编不同的同名同号不算歧义
            others = [x for x in others if not x[3] or x[3] in pcs]
        ambiguous = any(x[0] >= best[0] - 0.5 for x in others)
        if premise and not best[8] and others:  # 原文没有可印证的城镇 / 邮编，全国又不止一处同名同号：不选
            ambiguous = True
        written_pc = best[3] if best[3] in pcs else (pcs[0] if pcs else "")
        return NationalMatch(best[1], best[2] if premise else "", best[3], best[4], best[5], best[6], best[7], best[8],
                             premise, ambiguous,
                             [{"street": x[1], "number": x[2], "postcode": x[3], "area": x[4], "lat": x[5],
                               "lng": x[6], "source": "national"} for x in others[:max_others]], written_pc)


MANY_STREETS = 1500
TOWN_ROWS = 3000  # 按城镇召回同号门牌的上限，超过就加路名前缀条件
PREFIX_ROWS = 5000  # 写了邮编 / 城镇时，全国按路名前缀召回的上限


@lru_cache(maxsize=200000)
def _street_info(street: str) -> tuple:
    """官方路名的派生值（同一条路在全国库里有很多门牌，按路名缓存）：(词, 核心词, 编号, 核心词前 3 个字母, 是否编号道路)。"""
    words = tuple(norm(street).split())
    core, nums = _core(list(words))
    return words, tuple(core), tuple(nums), frozenset(w[:3] for w in core if len(w) >= 3), numbered_only(street)


def same_number(found: str, written: str) -> bool:
    """官方表的门牌（哥伦比亚 16B 15）与原文（16B-15）是否同一个。"""
    def key(n: str) -> str:
        return number_key(re.sub(r"^(\d+[A-Z]?)\s+(\d+[A-Z]?)$", r"\1-\2", n.strip().upper()))
    return key(found) == key(written)


def number_variants(number: str, cc: str = "") -> list[str]:
    """门牌的几种写法：区间 41-43 两头都可查；斜杠后面多是单元（波兰 15a/4、奥地利 16/75 Top、比利时 2/3 bus），
    只有捷克 / 斯洛伐克（登记号 / 街道号）两边都是门牌。"""
    n = number_key(number)
    out = [n]
    m = re.fullmatch(r"(\d+[A-Z]?)([-/])(\d+[A-Z]?)", n)
    if m:
        out.append(m.group(1))
        if m.group(2) == "-" or cc in ("CZ", "SK"):
            out.append(m.group(3))
    return list(dict.fromkeys(out))


def national(ref) -> NationalIndex:
    """与参考库放在同一目录（data/markets/<国家>/national.sqlite），随参考库缓存。"""
    idx = ref.__dict__.get("_national")
    if idx is None:
        idx = ref.__dict__["_national"] = NationalIndex(ref.market, ref.dir)
    return idx
