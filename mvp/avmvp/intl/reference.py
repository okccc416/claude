"""市场参考库：道路、片区、楼宇 / POI、邮编（B / C 类）以及官方地址点（A 类）。

来源（scripts/fetch_markets.py 下载的 Overture 数据）：
  道路   transportation 主题有名称的路段；同名且相邻（400 米内连通）的路段合并为一条道路
  片区   divisions 主题的行政区 / 社区（多语种名称），用边界多边形判断道路和 POI 属于哪些片区
  POI    places 主题；按编号哈希留出 20% 作测试，**不进参考库**
  邮编   A 类取官方地址表；B / C 类取 POI 邮编的中位位置（只能定位到片区）
  地址点 A 类官方地址表（门牌 + 道路 + 邮编 + 单元），存在 SQLite
  OSM 门牌 所有类别的第二门牌来源（scripts/fetch_osm_addresses.py），同一张表，编号从 OSM_ID_BASE 起

构建：python scripts/build_market_reference.py --markets AU,DE,...
"""

from __future__ import annotations

import hashlib
import math
import os
import pickle
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .fuzzy import FuzzyIndex
from .text import MARKET_LANG, TYPE_WORDS, core_key, fold, key, norm_postcode, postcode_prefix, skeleton, type_words

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("AV_MARKETS_DIR") or ROOT / "data" / "markets")  # 部署时可指定参考数据目录
_RT_RW = re.compile(r"^(RT|RW)\s?\d+$")
OSM_ID_BASE = 1_000_000_000  # 地址点编号 >= 这个数的来自 OSM（不是官方地址表）
# 可以当"楼宇"引用的 POI：商场、酒店、医院、学校、车站、公寓等（普通商户不算，很多商户直接以街道命名）
BUILDING_CATS = {"shopping_mall", "hotel", "hospital", "specialty_hospital", "college_university", "campus_building",
                 "high_school", "middle_school", "elementary_school", "airport", "train_station", "condominium",
                 "apartment", "public_plaza", "civic_center", "community_center", "market", "government_office",
                 "corporate_or_business_office", "industrial_facility_or_service", "cultural_center"}
BUILDING_WORDS = re.compile(r"\b(?:TOWER|TOWERS|PLAZA|BUILDING|BLDG|MALL|CENTRE|CENTER|COMPLEX|RESIDENCES?|"
                            r"APARTMENTS?|CONDO|MENARA|WISMA|GEDUNG|APARTEMEN|CITY|SQUARE|HOUSE|COURT|HOTEL|"
                            r"HOSPITAL|UNIVERSITY|MARKET|TERMINAL|STATION|EDIF[IÍ]CIO|TORRE|CONDOM[IÍ]NIO|PALAZZO|"
                            r"SHOPPING|GALERIA|CENTRO COMERCIAL)\b|برج|مبنى|مجمع|فندق|مول|อาคาร|ตึก|คอนโด|"
                            r"TÒA|CHUNG CƯ|CAO ỐC|ビル|タワー|センター|プラザ|ヒルズ|会館|ホテル", re.I)
# 冠词（核心键里也会去掉，但不能算"类型词"）：判断两个路名的类型词是否一致时不看它们
ARTICLES = {"DE", "DEL", "LA", "LAS", "LOS", "EL", "DA", "DO", "DAS", "DOS", "DI", "D", "DU", "L", "DES", "LE",
            "DELLA", "DEI", "DEGLI", "DELLE", "DELLO", "E"}


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


def street_names(n: dict | None) -> list[str]:
    """道路名称：括号里的常用名也单独作为名称（RK Patkar Marg (Waterfield Road) -> Waterfield Road / RK Patkar Marg）；
    括号里只有一个词的（(Peatonal)、(Norte)）是注释，不拆。"""
    out: list[str] = []
    for nm in names_of(n):
        for v in name_variants(nm):
            if v not in out and (v == nm or len(v.split()) >= 2):
                out.append(v)
    return out


def name_variants(name: str) -> list[str]:
    """带括号的路名拆成两个名称：EJE VIAL 1 ORIENTE (AVENIDA CANAL DE MIRAMONTES) -> 外面的正式名 + 括号里的常用名。"""
    m = re.fullmatch(r"\s*(.+?)\s*\((.+?)\)\s*", name or "")
    return [name] if not m else [name, m.group(2), m.group(1)]


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
        self.postcode_prefix: dict[str, tuple[float, float, int]] = {}  # 分级邮编的上一级（见 text.postcode_prefix）
        self.street_skel: dict[str, set[int]] = defaultdict(set)  # 阿拉伯文市场：转写骨架 -> 道路（见 text.skeleton）
        self.area_skel: dict[str, set[int]] = defaultdict(set)
        self.street_fuzzy: FuzzyIndex | None = None
        self.area_fuzzy: FuzzyIndex | None = None
        self.poi_fuzzy: FuzzyIndex | None = None
        self.poi_ids: list[int] = []
        self.has_addresses = False
        self.pc_complete = False  # 邮编表来自官方地址表（全量）：查无此邮编可以当作邮编错误
        self.poi_addr_count = 0  # 商户地址门牌点的个数（poiaddr.py）
        self.osm_count = 0  # OSM 门牌点的个数（官方表已有的门牌不重复收）
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
        """按道路（+ 门牌 / 邮编）查地址点（官方地址表 + OSM 门牌，编号 >= OSM_ID_BASE 的来自 OSM）。"""
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
        for k in ("_np", "_core_fuzzy", "_suffix"):
            s.pop(k, None)
        return s


def number_key(n: str) -> str:
    """门牌号规范化：去空格、统一大写（1 D -> 1D，110T 保留，190-200 保留）。"""
    return re.sub(r"\s+", "", str(n)).upper()


SLASH_BOTH = {"CZ", "SK", "PL", "LV", "LT"}  # 登记号 / 街道号（捷克、斯洛伐克）、转角楼的两个门牌（波兰、波罗的海）


def address_numbers(market: str, number: str, unit: str) -> tuple[str, list[str], str]:
    """官方地址表的门牌 -> (显示写法, 可查询的写法, 单元)。

    - 数字之间是空格的写成连字符：哥伦比亚 "66 33"（# 66-33）、葡萄牙 "8 10"（8-10）
    - 捷克：登记号 + 街道号（772 / 2）合写为 772/2，日常只写街道号 2，三种写法都能查到
    - 带斜杠的：斯洛伐克 145/4、波兰 100/102 每一部分都能查到；其他国家只有斜杠前的号码能单独查到
    """
    num = re.sub(r"^(\d+)\s*-\s*([A-Z])$", r"\1\2", str(number).strip().upper())  # 墨西哥 27-A -> 27A
    num = re.sub(r"^(\d+[A-Z]?)\s+(\d+[A-Z]?)$", r"\1-\2", num)
    unit = (unit or "").strip()
    if market == "JP":  # 日本的地址表是街区级（OpenAddresses jp/tokyo）：号码写作"街区-9"，只有街区号有意义
        num = num.split("-")[0]
    if market == "CZ" and unit and re.fullmatch(r"\d+[A-Za-z]?", unit):
        num, unit = f"{num}/{unit.upper()}", ""
    keys = [num]
    if "/" in num:
        parts = [x for x in num.split("/") if x]
        if market in SLASH_BOTH:  # 斜杠两边都是日常会单独写的号码
            keys += parts[::-1] if market in ("CZ", "SK") else parts  # 捷克 / 斯洛伐克：街道号（斜杠后）在前
        else:  # 其他国家斜杠后是附属号（爱沙尼亚 Kopli 103/16、克罗地亚 23/1），只有斜杠前的号码单独可查
            keys.append(parts[0])
    return num, list(dict.fromkeys(number_key(k) for k in keys)), unit


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
        if r["geometry"] is None:
            continue
        if aid is None:  # 边界跨进试点范围、但标注点在范围外的区（墨西哥城的 Tlalpan、Iztapalapa）：按边界补上
            nm = names_of(r["names"])
            if not nm or _RT_RW.match(nm[0].upper()):
                continue
            lat, lng = center(r["bbox"])
            aid = div_index[r["division_id"]] = len(ref.areas)
            ref.areas.append(Area(aid, nm[0], nm, r["subtype"], lat, lng))
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
        nm = street_names(s["names"])
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
    _add_road_refs(ref, log)

    # ---- 官方地址点（A 类）
    db = sqlite3.connect(d / "reference.sqlite")
    db.executescript("DROP TABLE IF EXISTS addr; DROP TABLE IF EXISTS poi;"
                     "CREATE TABLE addr(id INTEGER PRIMARY KEY, number TEXT, number_key TEXT, street INTEGER, "
                     "street_name TEXT, unit TEXT, postcode TEXT, locality TEXT, lat REAL, lng REAL);"
                     "CREATE TABLE poi(id INTEGER PRIMARY KEY, name TEXT, category TEXT, lat REAL, lng REAL, "
                     "street INTEGER, area INTEGER, postcode TEXT, is_bldg INTEGER);")
    street_by_key_near: dict[str, list[int]] = defaultdict(list)
    street_by_core_near: dict[str, list[int]] = defaultdict(list)
    for s in ref.streets:
        street_by_key_near[key(s.name, market)].append(s.id)
        for nm in s.names:
            street_by_core_near[core_key(nm, market)].append(s.id)
    official: set[tuple[int, str]] = set()  # 官方表已有的"道路 + 门牌"（OSM 不重复收）
    if cls == "A" and ((d / "addresses.parquet").exists() or (d / "extra_addresses.parquet").exists()):
        ref.has_addresses = True
        pc_acc: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
        cols = ["number", "street", "unit", "postcode", "address_levels", "bbox"]
        if (d / "addresses.parquet").exists() and "postal_city" in pq.read_schema(d / "addresses.parquet").names:
            cols.append("postal_city")
        rows = pq.read_table(d / "addresses.parquet", columns=cols).to_pylist() \
            if (d / "addresses.parquet").exists() else []
        n_overture = len(rows)
        if (d / "extra_addresses.parquet").exists():  # Overture 之外的官方开放地址（scripts/fetch_extra_addresses.py）
            extra = pq.read_table(d / "extra_addresses.parquet").to_pylist()
            rows += [dict(r, address_levels=None, extra=True) for r in extra]
        batch = []
        kcache: dict[str, tuple[str, str]] = {}
        aid = 0
        for i, r in enumerate(rows):
            if not r["street"] or not r["number"] or not re.search(r"\d", str(r["number"])):
                continue  # 没有门牌号的记录（维也纳市营住宅 "STG."、楼名）不当地址点
            lat, lng = center(r["bbox"])
            variants = kcache.get(r["street"]) or kcache.setdefault(
                r["street"], [(v, key(v, market), core_key(v, market)) for v in name_variants(r["street"])])
            sid = None
            for _, k, _ in variants:  # 括号里的常用名也试（EJE VIAL 1 ORIENTE (AVENIDA CANAL DE MIRAMONTES)）
                sid = _nearest_street(ref, street_by_key_near.get(k, []), lat, lng)
                if sid is not None:
                    break
            if sid is None:
                # 写法不同的同一条路（地址表 CALLE MADERA / 路网 Calle de la Madera、ulica Złota / Złota）：
                # 去掉类型词和冠词后一致、类型词不冲突、就在旁边，才算同一条路；地址表的写法记为别名
                for v, _, ck in variants:
                    if len(ck) < 4 or ck.isdigit():
                        continue
                    near = [x for x in street_by_core_near.get(ck, []) if _same_type(v, ref.streets[x].name, market)]
                    sid = _nearest_street(ref, near, lat, lng, max_m=300)
                    if sid is not None:
                        for v2, _, _ in variants:
                            if v2 not in ref.streets[sid].names:
                                ref.streets[sid].names.append(v2)
                        break
            if sid is None:  # 官方地址表里有、路网里没有名字的道路：新建一条
                sid = len(ref.streets)
                ref.streets.append(Street(sid, r["street"], [v for v, _, _ in variants], lat, lng,
                                          (lng, lat, lng, lat), points=[(lat, lng)]))
            for _, k, _ in variants:
                if sid not in street_by_key_near[k]:
                    street_by_key_near[k].append(sid)
            s = ref.streets[sid]
            s.bbox = (min(s.bbox[0], lng), min(s.bbox[1], lat), max(s.bbox[2], lng), max(s.bbox[3], lat))
            if len(s.points) < 400 and i % 7 == 0:
                s.points.append((lat, lng))
            levels = [x["value"] for x in (r["address_levels"] or []) if x.get("value")]
            locality = r.get("postal_city") or (levels[-1] if levels else "")
            pc = norm_postcode(r["postcode"], market)
            num, keys, unit = address_numbers(market, r["number"], r["unit"])
            if r.get("extra") and all((sid, nk) in official for nk in keys):
                continue  # 补充数据里与 Overture 地址表重复的门牌
            for nk in keys:
                batch.append((aid, num, nk, sid, r["street"], unit, pc, locality, lat, lng))
                official.add((sid, nk))
                aid += 1
            if pc:
                acc = pc_acc[pc]
                acc[0] += lat
                acc[1] += lng
                acc[2] += 1
            if len(batch) >= 50000:
                db.executemany("INSERT INTO addr VALUES (?,?,?,?,?,?,?,?,?,?)", batch)
                batch = []
        db.executemany("INSERT INTO addr VALUES (?,?,?,?,?,?,?,?,?,?)", batch)
        ref.postcodes = {pc: (a[0] / a[2], a[1] / a[2], int(a[2])) for pc, a in pc_acc.items()}
        # 有的国家地址表不带邮编（意大利、爱沙尼亚、新西兰、智利、哥伦比亚、日本）：邮编改从 POI 统计
        # 只有补充数据（斯德哥尔摩市、索非亚市）的不算全量：邮编表仍从 POI 补
        ref.pc_complete = len(ref.postcodes) >= 10 and n_overture > 0
        log(f"  官方地址点 {len(rows):,} 条（其中补充数据 {len(rows) - n_overture:,} 条），邮编 {len(ref.postcodes):,} 个")
        del rows, batch, kcache  # 澳洲地址表 360 万条：先释放再读 OSM 门牌
    osm_pc = _add_osm(ref, db, official, street_by_key_near, street_by_core_near, log)
    if (d / "extra_postcodes.parquet").exists():  # 全量邮编中心点（英国 Code-Point Open，见 scripts/fetch_extra_addresses.py）
        ref.postcodes = {norm_postcode(r["postcode"], market): (r["lat"], r["lng"], 1)
                         for r in pq.read_table(d / "extra_postcodes.parquet").to_pylist()}
        ref.pc_complete = True
        log(f"  邮编中心点 {len(ref.postcodes):,} 个（全量）")
    db.execute("CREATE INDEX addr_street ON addr(street, number_key)")
    db.execute("CREATE INDEX addr_pc ON addr(postcode, number_key)")

    # ---- 道路所属片区：道路上任一路段中点落在片区内即算（长路会跨多个片区）
    flat = [(s.id, pt) for s in ref.streets for pt in (s.points or [(s.lat, s.lng)])]
    for (sid, _), arr in zip(flat, areas_containing([x[1][0] for x in flat], [x[1][1] for x in flat])):
        st = ref.streets[sid]
        st.areas.extend(a for a in arr if a not in st.areas)
    arabic = MARKET_LANG.get(market) == "AR"
    initials = market in INITIALS_MARKETS
    for s in ref.streets:
        for nm in s.names:
            if key(nm, market):
                ref.street_keys[key(nm, market)].add(s.id)
            if initials:  # 人名道路的缩写别名：JALAN MOHAMMAD HUSNI THAMRIN -> JALAN MH THAMRIN
                for alias in initial_aliases(key(nm, market), market):
                    ref.street_keys[alias].add(s.id)
            if core_key(nm, market):
                ref.street_core[core_key(nm, market)].add(s.id)
            if arabic and _is_arabic(nm) and len(skeleton(nm)) >= 3:  # 只收阿拉伯文名称：拉丁名称走容错检索
                ref.street_skel[skeleton(nm)].add(s.id)
    if arabic:
        for a in ref.areas:
            for nm in a.names:
                if _is_arabic(nm) and len(skeleton(nm)) >= 3:
                    ref.area_skel[skeleton(nm)].add(a.id)
    if market == "JP":
        n = _japanese_aliases(ref)
        log(f"  町丁目罗马字别名 {n:,} 个")

    # ---- POI（留出 20% 作测试）
    places = pq.read_table(d / "places.parquet", columns=["id", "names", "basic_category", "addresses",
                                                          "bbox"]).to_pylist()
    keep = [p for p in places if (p["names"] or {}).get("primary") and not is_test_place(p["id"])]
    locs = [center(p["bbox"]) for p in keep]
    parea = areas_containing([x[0] for x in locs], [x[1] for x in locs])
    pc_acc2: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
    batch = []
    if not ref.pc_complete:  # OSM 门牌上的邮编比商户自填的准，一起统计
        for pc, a in osm_pc.items():
            acc = pc_acc2[pc]
            acc[0] += a[0]
            acc[1] += a[1]
            acc[2] += a[2]
    for i, (p, (lat, lng), ar) in enumerate(zip(keep, locs, parea)):
        addr = (p["addresses"] or [{}])[0]
        pc = norm_postcode(addr.get("postcode"), market)
        cat = p.get("basic_category") or ""
        is_bldg = int(cat in BUILDING_CATS or bool(BUILDING_WORDS.search(p["names"]["primary"])))
        batch.append((i, p["names"]["primary"], cat, lat, lng, -1, ar[0] if ar else -1, pc, is_bldg))
        if pc and not ref.pc_complete:
            acc = pc_acc2[pc]
            acc[0] += lat
            acc[1] += lng
            acc[2] += 1
    db.executemany("INSERT INTO poi VALUES (?,?,?,?,?,?,?,?,?)", batch)
    db.commit()
    db.close()
    if not ref.pc_complete:
        ref.postcodes = {pc: (a[0] / a[2], a[1] / a[2], int(a[2])) for pc, a in pc_acc2.items() if a[2] >= 3}
        pre: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
        for pc, a in pc_acc2.items():
            k = postcode_prefix(pc, market)
            if k:
                pre[k][0] += a[0]
                pre[k][1] += a[1]
                pre[k][2] += a[2]
        ref.postcode_prefix = {k: (a[0] / a[2], a[1] / a[2], int(a[2])) for k, a in pre.items() if a[2] >= 5}
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
    # ---- 商户地址门牌点（第二层门牌数据，见 poiaddr.py）
    from .poiaddr import derive
    derive(ref, log)
    ref.save()
    return ref


INITIALS_MARKETS = {"ID", "MY", "PH"}  # 道路多以人名命名、人名常写成缩写（M.H. Thamrin、K.H. Mas Mansyur）


def initial_aliases(k: str, market: str) -> list[str]:
    """把名称中间连续 2–3 个人名词换成首字母（最后一个词保留）：HAJI RANGKAYO RASUNA SAID -> HR RASUNA SAID。"""
    from .text import TYPE_WORDS
    types = type_words(market)
    toks = k.split()
    out = []
    for size in (2, 3):
        for i in range(len(toks) - size):  # 不含最后一个词
            run = toks[i:i + size]
            if any(t in types or not t.isalpha() or len(t) < 2 for t in run):
                continue
            out.append(" ".join(toks[:i] + ["".join(t[0] for t in run)] + toks[i + size:]))
    return out


def _same_type(a: str, b: str, market: str) -> bool:
    """两个路名的类型词（去掉冠词）一致，或其中一个没写类型词（CALLE MADERA ≈ Calle de la Madera ≠ Plaza Madera）。"""
    types = type_words(market) - ARTICLES
    ta, tb = set(key(a, market).split()) & types, set(key(b, market).split()) & types
    return not ta or not tb or ta <= tb or tb <= ta  # AVENIDA CALZADA DE LAS ARMAS ≈ Calzada de las Armas


def _japanese_aliases(ref: MarketReference) -> int:
    """日本：町丁目名只有日文（丸の内二丁目）。片区（町）有罗马字名称时，给道路加罗马字别名（MARUNOUCHI 2 CHOME），
    让 "2 Chome-7-9 Marunouchi" 这类写法也能对上。"""
    latin: dict[str, str] = {}  # 町名（日文）-> 罗马字：上高田一丁目 / Kami Takada 1 -> 上高田 -> KAMI TAKADA
    for a in ref.areas:
        ja = [n for n in a.names if re.search(r"[\u3040-\u30ff\u3400-\u9fff]", n)]
        en = [n for n in a.names if re.fullmatch(r"[A-Za-z0-9\u00C0-\u024F\s'\-]+", n)]
        if not ja or not en:
            continue
        town_en = re.sub(r"\s*\d+(?:\s*CHOME)?$", "", " ".join(key(en[0], ref.market).split())).strip()
        for j in ja:
            m = re.fullmatch(r"(.+?) \d+ CHOME", key(j, ref.market))
            if town_en:
                latin.setdefault(m.group(1) if m else key(j, ref.market), town_en)
    added = 0
    for s in ref.streets:
        m = re.fullmatch(r"(.+?) (\d+) CHOME", key(s.name, ref.market))
        town, chome = (m.group(1), m.group(2)) if m else (key(s.name, ref.market), None)
        en = latin.get(town)
        if not en:
            continue
        names = {en, en.replace(" ", "")}  # Minami Senju / Minamisenju
        for nm in list(names):  # 町的两种读法：本町 HONCHO / HONMACHI
            if nm.endswith("CHO"):
                names.add(nm[:-3] + "MACHI")
            elif nm.endswith("MACHI"):
                names.add(nm[:-5] + "CHO")
        for name in names:
            ref.street_keys[f"{name} {chome} CHOME" if chome else name].add(s.id)
            added += 1
    return added


def _is_arabic(text: str) -> bool:
    return bool(re.search(r"[؀-ۿ]", text))


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
    # 路网里同一条路常有断口（路口、桥、数据缺段）：约 100 米的细格子里相邻格子有同名路段，也算连通（断口 ≤ 约 200 米）
    fine: dict[tuple[int, int], int] = {}
    for i, it in enumerate(items):
        for lat, lng in (it[4] if len(it) > 4 else []):
            fine.setdefault((int(lat // 0.001), int(lng // 0.001)), i)
    for (a, b), i in fine.items():
        for da in (-1, 0, 1):
            for db in (-1, 0, 1):
                j = fine.get((a + da, b + db))
                if j is not None and j != i:
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


# 商户地址里常只写道路编号的市场（其他市场的 A10 / S100 这类编号容易和单元号混淆，不收）
ROAD_REF_MARKETS = {"PR", "IE", "GB"}


def _road_ref_names(market: str, ref_tag: str) -> list[str]:
    """OSM 道路编号 -> 可匹配的名称：波多黎各 PR-25 -> CARRETERA 25（解析时 PR-25 / Carr 25 都改写成这个）；
    其他市场原样（N11、A40、M50）。只收"字母 + 数字"的编号，纯数字编号会和门牌号混淆。"""
    out = []
    for r in ref_tag.split(";"):
        m = re.fullmatch(r"([A-Z]{1,3})[- ]?(\d{1,4}[A-Z]?)", r.strip().upper())
        if not m:
            continue
        out.append(f"CARRETERA {m.group(2)}" if market == "PR" else f"{m.group(1)}{m.group(2)}")
    return out


def _add_road_refs(ref: MarketReference, log) -> int:
    """带编号的道路（data/markets/{市场}/osm_road_refs.parquet）：按编号建道路（同编号的路段 400 米连通合并），
    名称为编号（和路名）。商户常只写编号：1822 PR-25、Carr 199、Unit 5, N7 Business Park。"""
    import pyarrow.parquet as pq

    path = ref.dir / "osm_road_refs.parquet"
    if ref.market not in ROAD_REF_MARKETS or not path.exists():
        return 0
    by_ref: dict[str, list[tuple]] = defaultdict(list)
    for r in pq.read_table(path).to_pylist():
        names = _road_ref_names(ref.market, r["ref"] or "")
        if not names:
            continue
        pts = list(zip(r["lats"], r["lngs"]))
        lats, lngs = r["lats"], r["lngs"]
        bb = {"xmin": min(lngs), "ymin": min(lats), "xmax": max(lngs), "ymax": max(lats)}
        for nm in names:
            by_ref[nm].append((sum(lats) / len(lats), sum(lngs) / len(lngs), bb,
                               [nm] + ([r["name"]] if r["name"] else []), pts))
    n = 0
    for nm, items in by_ref.items():
        for cluster in _clusters(items, 400.0):
            lat = sum(x[0] for x in cluster) / len(cluster)
            lng = sum(x[1] for x in cluster) / len(cluster)
            bb = (min(x[2]["xmin"] for x in cluster), min(x[2]["ymin"] for x in cluster),
                  max(x[2]["xmax"] for x in cluster), max(x[2]["ymax"] for x in cluster))
            names: list[str] = []
            for x in cluster:
                names += [v for v in x[3] if v not in names]
            ref.streets.append(Street(len(ref.streets), nm, names[:6], lat, lng, bb,
                                      length_m=haversine(bb[1], bb[0], bb[3], bb[2]),
                                      points=_thin([p for x in cluster for p in x[4]])))
            n += 1
    log(f"  带编号的道路 {n:,} 条（{len(by_ref):,} 个编号）")
    return n


# 开发集上加了 OSM 门牌反而变差的市场（东南亚、中东：OSM 门牌稀少且常挂错道路，开发集定位对 −6 到 −27 条 / 600），不用
OSM_SKIP_MARKETS = {"MY", "ID", "TH", "VN", "PH", "AE", "SA"}


def _osm_number(market: str, number: str, unit: str) -> tuple[str, str]:
    """OSM 的 addr:housenumber：多个号码只取第一个（12;14）；澳洲 / 新西兰的 14/59 是"单元 / 门牌"。"""
    number = number.split(";")[0].strip()
    m = re.fullmatch(r"([A-Za-z]?\d+[A-Za-z]?)\s*/\s*(\d+[A-Za-z]?)", number)
    if m and market in ("AU", "NZ"):
        return m.group(2), unit or m.group(1)
    return number, unit


def _add_osm(ref: MarketReference, db, official: set, by_key: dict, by_core: dict, log) -> dict:
    """OSM 门牌（data/markets/{市场}/osm_addresses.parquet）并入地址点表：
    - 道路名与路网一致（或去类型词后一致、类型词不冲突）且就在 300 米内才收；对不上的不新建道路
    - 官方表已有的"道路 + 门牌"不重复收
    - 带名称的商户节点，如果与留出测试的商户同名（相似度 >= 70）且相距 40 米内，不收：不能让测试商户的孪生记录替它作证
    返回 OSM 门牌上的邮编统计 {邮编: [纬度和, 经度和, 个数]}。"""
    import pyarrow.parquet as pq
    from rapidfuzz import fuzz

    path = ref.dir / "osm_addresses.parquet"
    if ref.market in OSM_SKIP_MARKETS or not path.exists():
        return {}
    market = ref.market
    cell = 0.0005
    test_grid: dict[tuple[int, int], list[tuple[float, float, str]]] = defaultdict(list)
    for p in pq.read_table(ref.dir / "places.parquet", columns=["id", "names", "bbox"]).to_pylist():
        if is_test_place(p["id"]):
            lat, lng = center(p["bbox"])
            test_grid[(int(lat // cell), int(lng // cell))].append((lat, lng, key((p["names"] or {}).get("primary")
                                                                               or "", market)))
    rows = pq.read_table(path).to_pylist()
    kcache: dict[str, list] = {}
    seen: set[tuple[int, str, str]] = set()
    pc_acc: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
    batch, twins, unlinked = [], 0, 0
    orphans: dict[tuple[str, int, int], list[dict]] = defaultdict(list)
    aid = OSM_ID_BASE
    for r in rows:
        if not r["number"] or not re.search(r"\d", r["number"]) or len(r["number"]) > 12:
            continue
        lat, lng = r["lat"], r["lng"]
        if r["name"]:
            nk = key(r["name"], market)
            a, b = int(lat // cell), int(lng // cell)
            if any(haversine(lat, lng, t[0], t[1]) <= 40 and fuzz.token_set_ratio(nk, t[2]) >= 70
                   for i in (-1, 0, 1) for j in (-1, 0, 1) for t in test_grid.get((a + i, b + j), ())):
                twins += 1
                continue
        variants = kcache.get(r["street"]) or kcache.setdefault(
            r["street"], [(v, key(v, market), core_key(v, market)) for v in name_variants(r["street"])])
        sid = None
        for _, k, _ in variants:
            sid = _nearest_street(ref, by_key.get(k, []), lat, lng, max_m=300)
            if sid is not None:
                break
        if sid is None:
            for v, _, ck in variants:
                if len(ck) < 4 or ck.isdigit():
                    continue
                near = [x for x in by_core.get(ck, []) if _same_type(v, ref.streets[x].name, market)]
                sid = _nearest_street(ref, near, lat, lng, max_m=300)
                if sid is not None:
                    break
        if sid is None:
            unlinked += 1
            orphans[(r["street"], int(lat // 0.03), int(lng // 0.03))].append(r)
            continue
        pc = norm_postcode(r["postcode"], market) if r["postcode"] else ""
        num, keys, unit = address_numbers(market, *_osm_number(market, r["number"], r["unit"]))
        for nk in keys:
            if (sid, nk) in official or (sid, nk, unit) in seen:
                continue
            seen.add((sid, nk, unit))
            batch.append((aid, num, nk, sid, r["street"], unit, pc, r["city"], lat, lng))
            aid += 1
        if pc:
            acc = pc_acc[pc]
            acc[0] += lat
            acc[1] += lng
            acc[2] += 1
    # 门牌挂在片区 / 小区名下（索非亚 ж.к. Младост 1 бл. 12、都柏林的住宅区、吉隆坡的 Taman）：路网里没有这个名字，
    # 同一名称在约 3 公里内有 3 个以上门牌时，按"道路"建一条，门牌照收
    estates = 0
    for (name, _, _), grp in orphans.items():
        if len(grp) < 3 or not key(name, market) or key(name, market).isdigit():
            continue
        lats, lngs = [g["lat"] for g in grp], [g["lng"] for g in grp]
        sid = len(ref.streets)
        ref.streets.append(Street(sid, name, [name], sum(lats) / len(lats), sum(lngs) / len(lngs),
                                  (min(lngs), min(lats), max(lngs), max(lats)),
                                  length_m=haversine(min(lats), min(lngs), max(lats), max(lngs)),
                                  points=[(g["lat"], g["lng"]) for g in grp[:400]]))
        estates += 1
        for g in grp:
            num, keys, unit = address_numbers(market, *_osm_number(market, g["number"], g["unit"]))
            pc = norm_postcode(g["postcode"], market) if g["postcode"] else ""
            for nk in keys:
                if (sid, nk, unit) not in seen:
                    seen.add((sid, nk, unit))
                    batch.append((aid, num, nk, sid, name, unit, pc, g["city"], g["lat"], g["lng"]))
                    aid += 1
    db.executemany("INSERT INTO addr VALUES (?,?,?,?,?,?,?,?,?,?)", batch)
    ref.osm_count = len(batch)
    log(f"  OSM 门牌点 {len(batch):,} 个（共 {len(rows):,} 条；道路对不上 {unlinked:,}，其中按片区名建道路 {estates:,} 条；"
        f"测试商户孪生记录 {twins:,}）")
    return pc_acc


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
