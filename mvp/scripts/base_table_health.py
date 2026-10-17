"""门址底表体检 + 补齐：把客户自己的门址底表（每行一条标准门址 + 坐标）逐条对照全国门址库（G-NAF，national.sqlite）。

对每条门址找"同路名、同门牌"的官方地址点，按距离分类：
  match_30m / match_30_500m       官方库里有，坐标吻合 / 偏一点
  suffix_differs                  路名差一个方位后缀（底表 DUNMORE ST，官方 DUNMORE STREET NORTH）
  street_ok_number_missing        附近有这条路，但官方库没有这个门牌（新建、改号、转角地块）
  match_far_500m+                 同路同门牌在 500 m 以外：底表坐标多半放错了地方
  street_elsewhere / street_not_found / lot_only / unparsed
对吻合的门址补上 suburb 和邮编（底表没有这两列）；统计 district 是否写错、同一 district 下的同名门址补上 suburb 后
能不能分开、一个坐标挂了多条路的"坐标热点"。--coverage 反查官方门址在底表里有没有（全量底表才有意义）。

报告只写汇总数字；--examples 才会把少量原始门址写进 json（只用于本地排查，不要提交）。
--enrich-out 输出逐行补齐结果（id、分类、距离、suburb、邮编、官方路名 / 门牌），给底表回填用。

  python scripts/base_table_health.py 底表.csv.xz --out reports/base_health.json [--coverage] [--enrich-out enrich.csv.gz]
  列名默认按悉尼底表（vec_id / address / x / y / district），别的表用 --cols id=...,address=...,lng=...,lat=...,district=...
"""

from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
import lzma
import math
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp.intl.reference import haversine, number_key  # noqa: E402
from avmvp.intl.text import key  # noqa: E402

# G-NAF 单元 / 楼层类型（全称和缩写）：UNIT / SE / CARS / VLLA / OFFC / FCTY / TNHS ……
FLAT = (r"(?:UNIT|U|SHOP|SHP|SUITE|SE|FLAT|APARTMENT|APT|VILLA|VLLA|TOWNHOUSE|TNHS|OFFICE|OFFC|FACTORY|FCTY|ROOM|"
        r"KIOSK|KSK|WAREHOUSE|WHSE|DUPLEX|DUPL|STUDIO|STU|STORE|STOR|STALL|STLL|CARSPACE|CARS|HOUSE|HSE|GARAGE|GRGE|"
        r"PENTHOUSE|PTHS|REAR|SITE|GATE|SHED|MBTH|ANT|BLDG|LOFT|WKSH)")
LEVEL = r"(?:LEVEL|LVL|L|FLOOR|FL|GROUND|G|BASEMENT|B|LG|UG|M)"
ADDR = re.compile(rf"^(?:{FLAT}\s+([0-9A-Z]+)\s+)?(?:{LEVEL}(?:\s+|(?=\d))([0-9A-Z]+)\s+)?(?:([A-Z]?\d+[A-Z]?)/)?"
                  rf"(\d+[A-Z]?)(?:\s*-\s*(\d+[A-Z]?))?\s+(.+)$")
LOT = re.compile(r"^LOT\s+\d+[A-Z]?\s+(\D.*)$")
RANGE = re.compile(r"(\d+)[A-Z]?-(\d+)[A-Z]?")
SUFFIX = {"NORTH", "SOUTH", "EAST", "WEST", "EXTENSION", "UPPER", "LOWER"}
CELL = 0.01  # 约 1 km 的格子，判断"附近有没有这条路"
NEAR_M, FAR_M = 30.0, 500.0
DEFAULT_COLS = {"id": "vec_id", "address": "address", "lng": "x", "lat": "y", "district": "district"}


def opener(path: str):
    return lzma.open if path.endswith(".xz") else gzip.open if path.endswith(".gz") else open


def cell(lat, lng):
    return (math.floor(lat / CELL), math.floor(lng / CELL))


class Keys:
    """路名比较键：规范化（含澳洲官方路类型缩写）后去掉空格（POWDER WORKS = POWDERWORKS）；去后缀键再去掉方位后缀。"""

    def __init__(self, cc):
        self.cc, self.cache = cc, {}

    def __call__(self, s: str) -> str:
        k = self.cache.get(s)
        if k is None:
            k = self.cache[s] = key(s.upper(), self.cc)
        return k


def flat(k):
    return k.replace(" ", "")


def unsuffixed(k):
    w = k.split()
    while len(w) > 2 and w[-1] in SUFFIX:
        w = w[:-1]
    return "".join(w)


def first_int(n):
    m = re.match(r"\d+", n)
    return int(m.group()) if m else 0


def bbox(path, cols, margin=0.15):
    lo_lat = lo_lng = 1e9; hi_lat = hi_lng = -1e9
    with opener(path)(path, "rt", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            lat, lng = float(row[cols["lat"]]), float(row[cols["lng"]])
            lo_lat, hi_lat, lo_lng, hi_lng = min(lo_lat, lat), max(hi_lat, lat), min(lo_lng, lng), max(hi_lng, lng)
    return lo_lat - margin, hi_lat + margin, lo_lng - margin, hi_lng + margin


def load_official(cc, box, sk):
    """底表范围内的官方门址：路名键 -> [(门牌键, 单元, 邮编, suburb, lat, lng, 路名)]；去后缀键 -> 同上；格子 -> 路名键集合。"""
    db = sqlite3.connect(f"file:{ROOT / 'data' / 'markets' / cc / 'national.sqlite'}?mode=ro", uri=True)
    by_street = collections.defaultdict(list); by_bare = collections.defaultdict(list)
    cells = collections.defaultdict(set)
    for st, nk, unit, pc, loc, lat, lng in db.execute(
            "SELECT street, nkey, unit, postcode, locality, lat, lng FROM addr "
            "WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?", box):
        k = sk(st)
        g = (nk, unit or "", pc or "", loc or "", lat, lng, st)
        by_street[flat(k)].append(g)
        by_bare[unsuffixed(k)].append(g)  # 不带后缀的路也进：底表多写或少写了方位后缀都能对上
        cells[cell(lat, lng)].add(flat(k))
    return by_street, by_bare, cells


def street_near(cells, fk, lat, lng, r=1):
    c0, c1 = cell(lat, lng)
    return any(fk in cells.get((c0 + i, c1 + j), ()) for i in range(-r, r + 1) for j in range(-r, r + 1))


def nearest(cand, nums, num, ranged, lat, lng):
    """门牌对得上的最近一条；底表只写了单号而官方存区间（16-20）时也算。返回 (距离, 官方行, 是否靠区间包含)。"""
    best = None
    for g in cand:
        if g[0] in nums:
            d = haversine(lat, lng, g[4], g[5])
            if best is None or d < best[0]:
                best = (d, g, False)
    if (best is None or best[0] > FAR_M) and not ranged:
        ni = first_int(num)
        for g in cand:
            m = RANGE.fullmatch(g[0])
            if m and int(m.group(1)) <= ni <= int(m.group(2)):
                d = haversine(lat, lng, g[4], g[5])
                if d <= FAR_M and (best is None or d < best[0]):
                    best = (d, g, True)
    return best


class Checker:
    def __init__(self, cc, box, coverage):
        self.sk = Keys(cc)
        self.by_street, self.by_bare, self.cells = load_official(cc, box, self.sk)
        self.base_keys = set() if coverage else None
        self.diag = collections.Counter()

    def check(self, address, lat, lng):
        """-> (分类, 距离, 官方行或 None, 单元 (底表单元, 官方是否有))"""
        up = re.sub(r"\s+", " ", address.upper().replace(",", " ")).strip()
        m = ADDR.match(up)
        if not m:
            lot = LOT.match(up)
            if not lot:
                return "unparsed", None, None, None
            # LOT n 路名：新分割地块的临时地址；看 30 m 内官方库有没有正式门牌
            near = [(haversine(lat, lng, g[4], g[5]), g) for g in self.by_street.get(flat(self.sk(lot.group(1))), [])]
            near = [x for x in near if x[0] <= NEAR_M]
            if near:
                self.diag["lot_has_official_number_30m"] += 1
                d, g = min(near, key=lambda x: x[0])
                return "lot_only", d, g, None
            return "lot_only", None, None, None
        unit, _level, unit2, num, num2, street = m.groups()
        unit = unit or unit2
        k = self.sk(street); fk = flat(k)
        nums = [number_key(f"{num}-{num2}"), number_key(num), number_key(num2)] if num2 else [number_key(num)]
        if self.base_keys is not None:
            self.base_keys.update((fk, n) for n in nums)
        cand = self.by_street.get(fk, [])
        best, via = nearest(cand, nums, num, bool(num2), lat, lng), "exact"
        if best is None or best[0] > FAR_M:
            b2 = nearest(self.by_bare.get(unsuffixed(k), []), nums, num, bool(num2), lat, lng)
            if b2 and b2[0] <= FAR_M:
                best, via = b2, "suffix"
        if best and best[0] <= FAR_M:
            d, g, by_range = best
            self.diag["range_contains"] += by_range
            cls = ("match_30m" if d <= NEAR_M else "match_30_500m") if via == "exact" else "suffix_differs"
            unit_hit = None
            if unit and via == "exact":
                units = {re.sub(r"\D", "", x[1]) for x in cand
                         if x[0] == g[0] and haversine(lat, lng, x[4], x[5]) <= NEAR_M}
                unit_hit = re.sub(r"\D", "", unit) in units
            return cls, d, g, unit_hit
        if street_near(self.cells, fk, lat, lng):
            local = [g for g in cand if haversine(lat, lng, g[4], g[5]) <= NEAR_M]
            if re.search(r"[A-Z]$", num) and any(g[0] == number_key(num[:-1]) for g in local):
                self.diag["nm_letter_suffix_only"] += 1  # 112A：官方只有 112
            elif local:
                self.diag["nm_other_number_30m"] += 1  # 坐标落在同路别的门牌上（转角、合并地块、改号）
            else:
                self.diag["nm_nothing_30m"] += 1  # 附近没有官方点：新建或官方快照里还没有
            return "street_ok_number_missing", None, None, None
        if best:
            return "match_far_500m+", best[0], None, None
        if cand or self.by_bare.get(unsuffixed(k)):
            return "street_elsewhere", None, None, None  # 路名在别处有，附近 1–2 km 内没有
        self.diag["nf_route_number"] += bool(re.fullmatch(r"[AM]\d+", street))  # 42 A28：路名写成了公路编号
        return "street_not_found", None, None, None


def district_report(district_loc):
    """每个 district 落在哪些 suburb；district 本身就是 suburb 名的，算写成别的 suburb 的比例。"""
    out = {}
    for dname, c in district_loc.items():
        n = sum(c.values()); known = n - c.get("", 0)
        rec = {"n": n, "matched": known, "top_suburbs": [(s, v) for s, v in c.most_common(6) if s][:5]}
        if known and dname.upper() in c and dname != "Sydney":  # Sydney 是 LGA（City of Sydney），不是 suburb
            rec["suburb_level"] = True
            rec["other_suburb"] = known - c[dname.upper()]
        out[dname] = rec
    return out


def same_name_report(groups):
    """同一 district 下同名门址（坐标相距 >10 m）：补上 suburb 后还有多少组分不开。"""
    out = collections.Counter()
    for v in groups.values():
        if len(v) < 2 or all(haversine(v[0][1], v[0][2], b[1], b[2]) <= 10 for b in v[1:]):
            continue
        out["groups"] += 1; out["rows"] += len(v)
        subs = [s for s, _, _ in v]
        out["some_row_unmatched" if not all(subs) else
            "resolved_by_suburb" if len(set(subs)) == len(subs) else "still_ambiguous"] += 1
    return dict(out)


def coverage_gaps(by_street, base_keys):
    """官方门址（路名 + 门牌，不分单元）在底表里没有的，按 suburb 汇总。"""
    tot = collections.Counter(); miss = collections.Counter(); pcs = {}; done = set()
    for fk, rows in by_street.items():
        for g in rows:
            nk, loc = g[0], g[3]
            if (fk, nk, loc) in done:
                continue
            done.add((fk, nk, loc)); tot[loc] += 1; pcs[loc] = g[2]
            miss[loc] += (fk, nk) not in base_keys
    rates = collections.Counter()
    for s in tot:
        r = miss[s] / tot[s]
        rates["<5%" if r < .05 else "5-20%" if r < .2 else "20-50%" if r < .5 else ">=50%"] += 1
    worst = sorted(((miss[s] / tot[s], miss[s], tot[s], s, pcs[s]) for s in tot if tot[s] >= 200), reverse=True)
    return {"official_addresses": sum(tot.values()), "missing": sum(miss.values()), "suburbs_by_miss_rate": dict(rates),
            "worst_suburbs": [{"suburb": s, "postcode": p, "official": t, "missing": mi, "rate": round(r, 3)}
                              for r, mi, t, s, p in worst[:40]]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("table")
    ap.add_argument("--out", required=True)
    ap.add_argument("--country", default="AU")
    ap.add_argument("--cols", default="", help="id=...,address=...,lng=...,lat=...,district=...")
    ap.add_argument("--coverage", action="store_true")
    ap.add_argument("--enrich-out", default="")
    ap.add_argument("--examples", type=int, default=0, help="每类写几条原始门址进 json（只用于本地排查）")
    a = ap.parse_args()
    cols = {**DEFAULT_COLS, **dict(kv.split("=", 1) for kv in a.cols.split(",") if kv)}
    box = bbox(a.table, cols)
    chk = Checker(a.country, box, a.coverage)
    st = collections.Counter(); by_id = collections.defaultdict(collections.Counter)
    by_style = collections.defaultdict(collections.Counter); dists = []; far_d = []
    enrich = collections.Counter(); examples = collections.defaultdict(list)
    district_loc = collections.defaultdict(collections.Counter)
    groups = collections.defaultdict(list)  # (地址, district) -> [(suburb, lat, lng)]
    at_coord = collections.defaultdict(set); coord_rows = collections.Counter()
    ew = None
    if a.enrich_out:
        ew = csv.writer(opener(a.enrich_out)(a.enrich_out, "wt", encoding="utf-8", newline=""))
        ew.writerow(["id", "class", "distance_m", "suburb", "postcode", "official_street", "official_number"])
    with opener(a.table)(a.table, "rt", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            addr = row[cols["address"]].strip()
            lat, lng = float(row[cols["lat"]]), float(row[cols["lng"]])
            cls, d, g, unit_hit = chk.check(addr, lat, lng)
            idf = "uuid" if "-" in row[cols["id"]] else "other"
            style = "upper" if addr == addr.upper() else "mixed"
            st["n"] += 1; st[cls] += 1
            by_id[idf][cls] += 1; by_id[idf]["n"] += 1; by_style[style][cls] += 1; by_style[style]["n"] += 1
            if d is not None and cls != "match_far_500m+" and cls != "lot_only":
                dists.append(d)
            if cls == "match_far_500m+":
                far_d.append(d)
            if g is not None:
                enrich["suburb"] += bool(g[3]); enrich["postcode"] += bool(g[2])
            if unit_hit is not None:
                st["unit_rows"] += 1; st["unit_found"] += unit_hit
            suburb = g[3] if g is not None else ""
            dist_name = row.get(cols["district"], "")
            district_loc[dist_name][suburb] += 1
            norm = re.sub(r"\s+", " ", addr.upper())
            groups[(norm, dist_name)].append((suburb, lat, lng))
            m = ADDR.match(norm)
            at_coord[(lat, lng)].add(chk.sk(m.group(6)) if m else norm); coord_rows[(lat, lng)] += 1
            if ew:
                ew.writerow([row[cols["id"]], cls, "" if d is None else round(d, 1), suburb,
                             g[2] if g is not None else "", g[6] if g is not None else "", g[0] if g is not None else ""])
            if len(examples[cls]) < a.examples:
                examples[cls].append(f"{addr} | {dist_name} | {lat:.5f},{lng:.5f}")
    dists.sort(); far_d.sort()
    pct = lambda xs, q: round(xs[min(len(xs) - 1, int(len(xs) * q))], 2) if xs else None
    res = {"official_rows_in_box": sum(len(v) for v in chk.by_street.values()), "counts": dict(st), "diag": dict(chk.diag),
           "by_id_format": {k: dict(v) for k, v in by_id.items()}, "by_case": {k: dict(v) for k, v in by_style.items()},
           "enrich": dict(enrich), "dist_m": {"p50": pct(dists, .5), "p90": pct(dists, .9), "p99": pct(dists, .99)},
           "far_dist_m": {"p10": pct(far_d, .1), "p50": pct(far_d, .5), "p90": pct(far_d, .9)},
           "same_name": same_name_report(groups),
           "hotspots": {f"streets>={t}": {"points": sum(1 for c, v in at_coord.items() if len(v) >= t),
                                          "rows": sum(coord_rows[c] for c, v in at_coord.items() if len(v) >= t)}
                        for t in (3, 5, 10)},
           "districts": district_report(district_loc)}
    if a.coverage:
        res["coverage"] = coverage_gaps(chk.by_street, chk.base_keys)
    if a.examples:
        res["examples"] = examples
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k not in ("examples", "districts")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
