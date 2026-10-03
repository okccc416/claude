"""商户地址门牌点：把参考库里商户自填的地址解析成"道路 + 门牌 -> 坐标"，作为官方地址表之外的第二层门牌数据。

地图公司（Google 等）在官方地址表之外，也用商户 / 用户提交的地址补门牌。这里用 Overture POI 做同样的事：
  - 只用参考库里的商户（按编号哈希留出的 20% 测试商户不用）
  - 同一个商户在不同来源里的重复记录（名称相近、相距 40 米内，或地址相同、相距 60 米内）也不用：
    不能让测试商户的"孪生记录"替它自己作证
  - 解析出的道路必须是完全一致或去类型词后一致（不用纠错得来的道路），商户坐标离这条路 150 米以内
  - 同一"道路 + 门牌"的多家商户取中位位置，离中位超过 150 米的不计；记下有几家商户印证（n）

用法：构建参考库时自动生成（reference.build 最后一步）；也可以单独刷新：python scripts/derive_poi_addresses.py
结果存在 reference.sqlite 的 poiaddr 表；引擎在官方地址表查不到门牌时使用（原因码 PREMISE_FROM_POI）。
"""

from __future__ import annotations

import re
import statistics
from collections import defaultdict

from rapidfuzz import fuzz

from .reference import MarketReference, center, haversine, is_test_place, number_key
from .text import key

CELL = 0.0005  # 约 50 米的格子（找孪生记录用）


def _cells(lat: float, lng: float):
    a, b = int(lat // CELL), int(lng // CELL)
    return [(a + i, b + j) for i in (-1, 0, 1) for j in (-1, 0, 1)]


def derive(ref: MarketReference, log=print, limit: int | None = None) -> int:
    import pyarrow.parquet as pq

    from .engine import dist_to_street
    from .parse import HOUSE_NO, RuleParser

    market = ref.market
    places = pq.read_table(ref.dir / "places.parquet", columns=["id", "names", "addresses", "bbox"]).to_pylist()
    test_grid: dict[tuple[int, int], list[tuple[float, float, str, str]]] = defaultdict(list)
    keep = []
    for p in places:
        name = (p["names"] or {}).get("primary") or ""
        addr = (p["addresses"] or [{}])[0] or {}
        ff = (addr.get("freeform") or "").strip()
        lat, lng = center(p["bbox"])
        if is_test_place(p["id"]):
            test_grid[(int(lat // CELL), int(lng // CELL))].append((lat, lng, key(name, market), key(ff, market)))
        elif ff and re.search(r"\d", ff):
            keep.append((name, ff, (addr.get("postcode") or "").strip(), lat, lng))
    rp = RuleParser(ref)
    acc: dict[tuple[int, str], list[tuple[float, float, str]]] = defaultdict(list)
    twins = parsed = 0
    for name, ff, pc, lat, lng in keep[:limit]:
        nk, fk = key(name, market), key(ff, market)
        twin = False
        for c in _cells(lat, lng):
            for tlat, tlng, tname, tff in test_grid.get(c, ()):
                d = haversine(lat, lng, tlat, tlng)
                if (d <= 40 and fuzz.token_set_ratio(nk, tname) >= 70) or (d <= 60 and fk == tff):
                    twin = True
                    break
            if twin:
                break
        if twin:
            twins += 1
            continue
        p = rp.parse(f"{ff}, {pc}" if pc else ff)
        if not p.number or not HOUSE_NO.match(p.number):
            continue
        spans = [s for s in p.streets if s.how in ("exact", "core") and len(s.ids) <= 40]
        if not spans:
            continue
        best = None
        for s in spans:
            for sid in s.ids:
                d = dist_to_street(ref, sid, lat, lng)
                if d <= 150 and (best is None or d < best[1]):
                    best = (sid, d)
        if best is None:
            continue
        parsed += 1
        acc[(best[0], number_key(p.number))].append((lat, lng, p.number))
    rows = []
    for (sid, nk), pts in acc.items():
        mlat = statistics.median(x[0] for x in pts)
        mlng = statistics.median(x[1] for x in pts)
        near = [x for x in pts if haversine(mlat, mlng, x[0], x[1]) <= 150]
        if not near:
            continue
        rows.append((sid, nk, near[0][2], sum(x[0] for x in near) / len(near), sum(x[1] for x in near) / len(near),
                     len(near)))
    db = ref.db
    db.executescript("DROP TABLE IF EXISTS poiaddr; CREATE TABLE poiaddr(street INTEGER, number_key TEXT, number TEXT, "
                     "lat REAL, lng REAL, n INTEGER);")
    db.executemany("INSERT INTO poiaddr VALUES (?,?,?,?,?,?)", rows)
    db.execute("CREATE INDEX poiaddr_street ON poiaddr(street, number_key)")
    db.commit()
    ref.poi_addr_count = len(rows)
    log(f"  商户地址门牌点 {len(rows):,} 个（{parsed:,} 家商户解析成功，排除孪生记录 {twins:,} 条）")
    return len(rows)


def lookup(ref: MarketReference, street: int, numbers: list[str]) -> dict | None:
    """按道路 + 门牌（几种等价写法）查商户地址门牌点；印证的商户多的优先。"""
    if not getattr(ref, "poi_addr_count", 0):
        return None
    for nk in numbers:
        r = ref.db.execute("SELECT number, lat, lng, n FROM poiaddr WHERE street=? AND number_key=? ORDER BY n DESC "
                           "LIMIT 1", (street, number_key(nk))).fetchone()
        if r:
            return {"id": -2, "number": r[0], "street": street, "unit": "", "postcode": "", "locality": "",
                    "lat": r[1], "lng": r[2], "n": r[3]}
    return None
