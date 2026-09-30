"""市场参考库：道路、片区、楼宇 / POI、邮编（B / C 类）以及官方地址点（A 类）。

来源（scripts/fetch_markets.py 下载的 Overture 数据）：
  道路   transportation 主题有名称的路段；同名且相邻（400 米内连通）的路段合并为一条道路
  片区   divisions 主题的行政区 / 社区（多语种名称），用边界多边形判断道路和 POI 属于哪些片区
  POI    places 主题；按编号哈希留出 20% 作测试，**不进参考库**
  邮编   A 类取官方地址表；B / C 类取 POI 邮编的中位位置（只能定位到片区）
  地址点 A 类官方地址表（门牌 + 道路 + 邮编 + 单元），存在 SQLite

构建：python scripts/build_market_reference.py --markets AU,DE,...
"""

from __future__ import annotations

import hashlib
import math
import pickle
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .fuzzy import FuzzyIndex
from .text import MARKET_LANG, core_key, key, skeleton

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "markets"
_RT_RW = re.compile(r"^(RT|RW)\s?\d+$")
# 可以当"楼宇"引用的 POI：商场、酒店、医院、学校、车站、公寓等（普通商户不算，很多商户直接以街道命名）
BUILDING_CATS = {"shopping_mall", "hotel", "hospital", "specialty_hospital", "college_university", "campus_building",
                 "high_school", "middle_school", "elementary_school", "airport", "train_station", "condominium",
                 "apartment", "public_plaza", "civic_center", "community_center", "market", "government_office",
                 "corporate_or_business_office", "industrial_facility_or_service", "cultural_center"}
BUILDING_WORDS = re.compile(r"\b(?:TOWER|TOWERS|PLAZA|BUILDING|BLDG|MALL|CENTRE|CENTER|COMPLEX|RESIDENCES?|"
                            r"APARTMENTS?|CONDO|MENARA|WISMA|GEDUNG|APARTEMEN|CITY|SQUARE|HOUSE|COURT|HOTEL|"
                            r"HOSPITAL|UNIVERSITY|MARKET|TERMINAL|STATION)\b|برج|مبنى|مجمع|فندق|مول|อาคาร|ตึก|คอนโด|"
                            r"TÒA|CHUNG CƯ|CAO ỐC", re.I)


def is_test_place(place_id: str) -> bool:
    """POI 留出规则：编号哈希的 20% 作测试集，不进参考库。"""
    return int(hashlib.sha1(place_id.encode()).hexdigest()[:8], 16) % 5 == 0


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """两点距离（米）。"""
    p = math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lng2 - lng1) * p / 2) ** 2)
    return 12742000 * math.asin(math.sqrt(min(1.0, a)))


@dataclass
class Street:
    id: int
    name: str
    names: list[str]
    lat: float
    lng: float
    bbox: tuple[float, float, float, float]
    areas: list[int] = field(default_factory=list)
    length_m: float = 0.0
    points: list[tuple[float, float]] = field(default_factory=list)  # 沿线的点（约 80 米一个）


@dataclass
class Area:
    id: int
    name: str
    names: list[str]
    subtype: str
    lat: float
    lng: float
    radius_m: float = 1500.0  # 没有边界时按半径近似
    has_poly: bool = False  # 有边界多边形（没有边界的片区范围不确定，不据此扣分）


def names_of(n: dict | None) -> list[str]:
    """Overture names 结构 -> 去重的名称列表（主名称 + 各语种常用名）。"""
    if not n:
        return []
    out = [n.get("primary")] if n.get("primary") else []
    common = n.get("common") or []
    items = common.items() if isinstance(common, dict) else common
    for _, v in items:
        if v and v not in out:
            out.append(v)
    return out


def center(bbox: dict) -> tuple[float, float]:
    return (bbox["ymin"] + bbox["ymax"]) / 2, (bbox["xmin"] + bbox["xmax"]) / 2


class MarketReference:
    """一个市场的参考库。内存里放道路 / 片区 / 邮编与检索索引，POI 与地址点放 SQLite。"""

    def __init__(self, market: str, root: Path | None = None):
        self.market = market
        self.dir = (root or DATA) / market
        self.streets: list[Street] = []
        self.areas: list[Area] = []
        self.street_keys: dict[str, set[int]] = defaultdict(set)  # 完整键 -> 道路
        self.area_keys: dict[str, set[int]] = defaultdict(set)
        self.street_core: dict[str, set[int]] = defaultdict(set)  # 核心键（去掉类型词）-> 道路
        self.area_core: dict[str, set[int]] = defaultdict(set)
        self.postcodes: dict[str, tuple[float, float, int]] = {}  # 邮编 -> (纬度, 经度, 条数)
        self.street_skel: dict[str, set[int]] = defaultdict(set)  # 阿拉伯文市场：转写骨架 -> 道路（见 text.skeleton）
        self.area_skel: dict[str, set[int]] = defaultdict(set)
        self.street_fuzzy: FuzzyIndex | None = None
        self.area_fuzzy: FuzzyIndex | None = None
        self.poi_fuzzy: FuzzyIndex | None = None
        self.poi_ids: list[int] = []
        self.has_addresses = False
        self._db: sqlite3.Connection | None = None

    # ------------------------------------------------------------------ 查询
    @property
    def db(self) -> sqlite3.Connection:
        if self._db is None:
            self._db = sqlite3.connect(self.dir / "reference.sqlite", check_same_thread=False)
        return self._db

    def poi(self, pid: int) -> dict:
        r = self.db.execute("SELECT id, name, category, lat, lng, street, area, postcode FROM poi WHERE id=?",
                            (pid,)).fetchone()
        return dict(zip(("id", "name", "category", "lat", "lng", "street", "area", "postcode"), r))

    def addresses(self, street_ids: list[int], number: str | None = None, postcode: str | None = None) -> list[dict]:
        """A 类：按道路（+ 门牌 / 邮编）查官方地址点。"""
        if not street_ids:
            return []
        q = f"SELECT id, number, street, unit, postcode, locality, lat, lng FROM addr WHERE street IN " \
            f"({','.join('?' * len(street_ids))})"
        args: list = list(street_ids)
        if number:
            q += " AND number_key=?"
            args.append(number_key(number))
        if postcode:
            q += " AND postcode=?"
            args.append(postcode)
        cols = ("id", "number", "street", "unit", "postcode", "locality", "lat", "lng")
        return [dict(zip(cols, r)) for r in self.db.execute(q + " LIMIT 400", args)]

    def units_at(self, street_id: int, number: str) -> int:
        r = self.db.execute("SELECT COUNT(DISTINCT unit) FROM addr WHERE street=? AND number_key=? AND unit != ''",
                            (street_id, number_key(number))).fetchone()
        return r[0] if r else 0

    # ------------------------------------------------------------------ 存取
    def save(self) -> None:
        db, self._db = self._db, None
        with open(self.dir / "reference.pkl", "wb") as f:
            pickle.dump(self, f)
        self._db = db

    @classmethod
    def load(cls, market: str, root: Path | None = None) -> "MarketReference":
        path = (root or DATA) / market / "reference.pkl"
        with open(path, "rb") as f:
            ref = pickle.load(f)
        ref.dir = path.parent
        ref._db = None
        return ref

    def __getstate__(self):
        s = self.__dict__.copy()
        s["_db"] = None
        s.pop("_np", None)
        return s


def number_key(n: str) -> str:
    """门牌号规范化：去空格、统一大写（1 D -> 1D，110T 保留，190-200 保留）。"""
    return re.sub(r"\s+", "", str(n)).upper()


# ---------------------------------------------------------------------------------------------- 构建
def build(market: str, cls: str, log=print, root: Path | None = None) -> MarketReference:
    import pyarrow.parquet as pq
    from shapely import STRtree, from_wkb, points

    ref = MarketReference(market, root)
    d = ref.dir
    # ---- 片区（点 + 边界）
    divs = pq.read_table(d / "divisions.parquet").to_pylist()
    div_index: dict[str, int] = {}
    for r in divs:
        nm = names_of(r["names"])
        if not nm or _RT_RW.match(nm[0].upper()):  # 印尼 RT / RW 编号没有上级就无法区分，不作片区名
            continue
        lat, lng = center(r["bbox"])
        a = Area(len(ref.areas), nm[0], nm, r["subtype"], lat, lng)
        div_index[r["id"]] = a.id
        ref.areas.append(a)
    polys, poly_area = [], []
    for r in pq.read_table(d / "division_areas.parquet").to_pylist():
        aid = div_index.get(r["division_id"])
        if aid is None or r["geometry"] is None:
            continue
        g = from_wkb(r["geometry"])
        polys.append(g)
        poly_area.append(aid)
        b = r["bbox"]
        ref.areas[aid].radius_m = max(haversine(b["ymin"], b["xmin"], b["ymax"], b["xmax"]) / 2, 300)
        ref.areas[aid].has_poly = True
    tree = STRtree(polys) if polys else None

    def areas_containing(lats: list[float], lngs: list[float]) -> list[list[int]]:
        out: list[list[int]] = [[] for _ in lats]
        if tree is None or not lats:
            return out
        pi, gi = tree.query(points(lngs, lats), predicate="within")
        for p, g in zip(pi, gi):
            out[p].append(poly_area[g])
        return out

    for a in ref.areas:
        for nm in a.names:
            if key(nm, market):
                ref.area_keys[key(nm, market)].add(a.id)
            if core_key(nm, market, "area"):
                ref.area_core[core_key(nm, market, "area")].add(a.id)
    log(f"  片区 {len(ref.areas):,} 个（有边界 {len(polys):,}）")

    # ---- 道路：同名路段按 400 米连通合并；沿线形每隔约 80 米取一个点（长路按片区 / 邮编就近定位、算距离用）
    segs = pq.read_table(d / "segments.parquet").to_pylist()
    seg_pts = _densify([s.get("geometry") for s in segs])
    by_name: dict[str, list[tuple]] = defaultdict(list)
    for s, pts in zip(segs, seg_pts):
        nm = names_of(s["names"])
        if not nm:
            continue
        lat, lng = center(s["bbox"])
        by_name[key(nm[0], market)].append((lat, lng, s["bbox"], nm, pts or [(lat, lng)]))
    for k, items in by_name.items():
        for cluster in _clusters(items, 400.0):
            lat = sum(x[0] for x in cluster) / len(cluster)
            lng = sum(x[1] for x in cluster) / len(cluster)
            bb = (min(x[2]["xmin"] for x in cluster), min(x[2]["ymin"] for x in cluster),
                  max(x[2]["xmax"] for x in cluster), max(x[2]["ymax"] for x in cluster))
            names: list[str] = []
            for x in cluster:
                names += [n for n in x[3] if n not in names]
            length = haversine(bb[1], bb[0], bb[3], bb[2])
            pts = _thin([p for x in cluster for p in x[4]])
            ref.streets.append(Street(len(ref.streets), names[0], names[:6], lat, lng, bb, length_m=length,
                                      points=pts))
    log(f"  道路 {len(ref.streets):,} 条（路段 {len(segs):,}）")

    # ---- 官方地址点（A 类）
    db = sqlite3.connect(d / "reference.sqlite")
    db.executescript("DROP TABLE IF EXISTS addr; DROP TABLE IF EXISTS poi;"
                     "CREATE TABLE addr(id INTEGER PRIMARY KEY, number TEXT, number_key TEXT, street INTEGER, "
                     "street_name TEXT, unit TEXT, postcode TEXT, locality TEXT, lat REAL, lng REAL);"
                     "CREATE TABLE poi(id INTEGER PRIMARY KEY, name TEXT, category TEXT, lat REAL, lng REAL, "
                     "street INTEGER, area INTEGER, postcode TEXT, is_bldg INTEGER);")
    street_by_key_near: dict[str, list[int]] = defaultdict(list)
    for s in ref.streets:
        street_by_key_near[key(s.name, market)].append(s.id)
    if cls == "A" and (d / "addresses.parquet").exists():
        ref.has_addresses = True
        pc_acc: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
        rows = pq.read_table(d / "addresses.parquet", columns=["number", "street", "unit", "postcode",
                                                               "address_levels", "bbox"]).to_pylist()
        batch = []
        kcache: dict[str, str] = {}
        for i, r in enumerate(rows):
            if not r["street"] or not r["number"]:
                continue
            lat, lng = center(r["bbox"])
            k = kcache.get(r["street"])
            if k is None:
                k = kcache[r["street"]] = key(r["street"], market)
            sid = _nearest_street(ref, street_by_key_near.get(k, []), lat, lng)
            if sid is None:  # 官方地址表里有、路网里没有名字的道路：新建一条
                sid = len(ref.streets)
                ref.streets.append(Street(sid, r["street"], [r["street"]], lat, lng, (lng, lat, lng, lat),
                                          points=[(lat, lng)]))
                street_by_key_near[k].append(sid)
            s = ref.streets[sid]
            s.bbox = (min(s.bbox[0], lng), min(s.bbox[1], lat), max(s.bbox[2], lng), max(s.bbox[3], lat))
            if len(s.points) < 400 and i % 7 == 0:
                s.points.append((lat, lng))
            levels = [x["value"] for x in (r["address_levels"] or []) if x.get("value")]
            pc = (r["postcode"] or "").replace(" ", "").upper()
            batch.append((i, str(r["number"]), number_key(r["number"]), sid, r["street"], r["unit"] or "", pc,
                          levels[-1] if levels else "", lat, lng))
            if pc:
                acc = pc_acc[pc]
                acc[0] += lat
                acc[1] += lng
                acc[2] += 1
            if len(batch) >= 50000:
                db.executemany("INSERT INTO addr VALUES (?,?,?,?,?,?,?,?,?,?)", batch)
                batch = []
        db.executemany("INSERT INTO addr VALUES (?,?,?,?,?,?,?,?,?,?)", batch)
        db.execute("CREATE INDEX addr_street ON addr(street, number_key)")
        db.execute("CREATE INDEX addr_pc ON addr(postcode, number_key)")
        ref.postcodes = {pc: (a[0] / a[2], a[1] / a[2], int(a[2])) for pc, a in pc_acc.items()}
        log(f"  官方地址点 {len(rows):,} 条，邮编 {len(ref.postcodes):,} 个")

    # ---- 道路所属片区：道路上任一路段中点落在片区内即算（长路会跨多个片区）
    flat = [(s.id, pt) for s in ref.streets for pt in (s.points or [(s.lat, s.lng)])]
    for (sid, _), arr in zip(flat, areas_containing([x[1][0] for x in flat], [x[1][1] for x in flat])):
        st = ref.streets[sid]
        st.areas.extend(a for a in arr if a not in st.areas)
    arabic = MARKET_LANG.get(market) == "AR"
    for s in ref.streets:
        for nm in s.names:
            if key(nm, market):
                ref.street_keys[key(nm, market)].add(s.id)
            if core_key(nm, market):
                ref.street_core[core_key(nm, market)].add(s.id)
            if arabic and len(skeleton(nm)) >= 3:
                ref.street_skel[skeleton(nm)].add(s.id)
    if arabic:
        for a in ref.areas:
            for nm in a.names:
                if len(skeleton(nm)) >= 3:
                    ref.area_skel[skeleton(nm)].add(a.id)

    # ---- POI（留出 20% 作测试）
    places = pq.read_table(d / "places.parquet", columns=["id", "names", "basic_category", "addresses",
                                                          "bbox"]).to_pylist()
    keep = [p for p in places if (p["names"] or {}).get("primary") and not is_test_place(p["id"])]
    locs = [center(p["bbox"]) for p in keep]
    parea = areas_containing([x[0] for x in locs], [x[1] for x in locs])
    pc_acc2: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
    batch = []
    for i, (p, (lat, lng), ar) in enumerate(zip(keep, locs, parea)):
        addr = (p["addresses"] or [{}])[0]
        pc = (addr.get("postcode") or "").replace(" ", "").upper()
        cat = p.get("basic_category") or ""
        is_bldg = int(cat in BUILDING_CATS or bool(BUILDING_WORDS.search(p["names"]["primary"])))
        batch.append((i, p["names"]["primary"], cat, lat, lng, -1, ar[0] if ar else -1, pc, is_bldg))
        if pc and not ref.has_addresses:
            acc = pc_acc2[pc]
            acc[0] += lat
            acc[1] += lng
            acc[2] += 1
    db.executemany("INSERT INTO poi VALUES (?,?,?,?,?,?,?,?,?)", batch)
    db.commit()
    db.close()
    if not ref.has_addresses:
        ref.postcodes = {pc: (a[0] / a[2], a[1] / a[2], int(a[2])) for pc, a in pc_acc2.items() if a[2] >= 3}
    ref.poi_ids = list(range(len(keep)))
    log(f"  POI {len(keep):,} 个（留出测试 {len(places) - len(keep):,} 个），邮编 {len(ref.postcodes):,} 个")

    # ---- 模糊检索索引
    ref.street_fuzzy = FuzzyIndex({k: sorted(v) for k, v in ref.street_keys.items()})
    ref.area_fuzzy = FuzzyIndex({k: sorted(v) for k, v in ref.area_keys.items()})
    poi_keys: dict[str, list[int]] = defaultdict(list)
    for i, p in enumerate(keep):
        k = key(p["names"]["primary"], market)
        # 只收"楼宇类" POI；名字本身就是道路 / 片区名的（如叫 "Taft Avenue" 的商户）不收
        if 3 <= len(k) <= 60 and batch[i][-1] and k not in ref.street_keys and k not in ref.area_keys:
            poi_keys[k].append(i)
    ref.poi_fuzzy = FuzzyIndex(poi_keys)
    ref.save()
    return ref


def _densify(wkbs: list, step_deg: float = 0.0008) -> list[list[tuple[float, float]]]:
    """路段线形 -> 沿线的点（纬度, 经度），相邻点间隔不超过约 80 米。没有线形时返回空列表。"""
    import numpy as np
    from shapely import from_wkb, get_coordinates, segmentize

    out: list[list[tuple[float, float]]] = [[] for _ in wkbs]
    have = [i for i, w in enumerate(wkbs) if w]
    if not have:
        return out
    geoms = segmentize(from_wkb([wkbs[i] for i in have]), step_deg)
    coords, idx = get_coordinates(geoms, return_index=True)
    for (x, y), j in zip(np.round(coords, 6).tolist(), idx.tolist()):
        out[have[j]].append((y, x))
    return out


def _thin(pts: list[tuple[float, float]], cell: float = 0.0004, cap: int = 1500) -> list[tuple[float, float]]:
    """去掉相距不到约 40 米的重复点；点太多时均匀抽样（极长的道路）。"""
    seen, out = set(), []
    for p in pts:
        k = (round(p[0] / cell), round(p[1] / cell))
        if k not in seen:
            seen.add(k)
            out.append(p)
    if len(out) > cap:
        out = out[:: len(out) // cap + 1]
    return out


def _clusters(items: list, radius: float, cell_deg: float = 0.0015) -> list[list]:
    """同名路段连通聚类（并查集）：沿线点落在同一个约 150 米格子里（首尾相接、双向分隔车道），
    或路段中心相距 radius 米内，视为同一条路。"""
    n = len(items)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    owner: dict[tuple[int, int], int] = {}
    for i, it in enumerate(items):
        for lat, lng in (it[4] if len(it) > 4 else []):
            c = (int(lat // cell_deg), int(lng // cell_deg))
            j = owner.setdefault(c, i)
            if j != i:
                parent[find(i)] = find(j)

    cell = radius / 111000
    grid: dict[tuple[int, int], list[int]] = defaultdict(list)
    for i, it in enumerate(items):
        grid[(int(it[0] / cell), int(it[1] / cell))].append(i)
    for (gx, gy), idx in grid.items():
        near = [j for dx in (-1, 0, 1) for dy in (-1, 0, 1) for j in grid.get((gx + dx, gy + dy), [])]
        for i in idx:
            for j in near:
                if j > i and haversine(items[i][0], items[i][1], items[j][0], items[j][1]) <= radius:
                    parent[find(i)] = find(j)
    groups: dict[int, list] = defaultdict(list)
    for i, it in enumerate(items):
        groups[find(i)].append(it)
    return list(groups.values())


def _nearest_street(ref: MarketReference, ids: list[int], lat: float, lng: float, max_m: float = 1500) -> int | None:
    best, bd = None, max_m
    for i in ids:
        s = ref.streets[i]
        # 到道路外包框的距离（框内为 0）
        clat = min(max(lat, s.bbox[1]), s.bbox[3])
        clng = min(max(lng, s.bbox[0]), s.bbox[2])
        dist = haversine(lat, lng, clat, clng)
        if dist < bd:
            best, bd = i, dist
    return best
