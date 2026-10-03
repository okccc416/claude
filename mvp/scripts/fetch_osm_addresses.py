"""下载各试点城市的 OpenStreetMap 门牌数据（addr:housenumber），存成 data/markets/{国家代码}/osm_addresses.parquet。

官方地址表之外的第二个门牌来源：Overture 的地址主题只覆盖部分国家，有的国家只有部分门牌（葡萄牙、墨西哥、哥伦比亚），
没有官方表的国家（英国、爱尔兰、马来西亚、印度、波多黎各……）完全没有门牌。OSM 志愿者录入的门牌在这些城市覆盖不一，
但录入的门牌本身位置准，地图公司也普遍用它补数据。

来源：BBBike 城市范围摘录（download.bbbike.org，每周更新）；没有城市摘录的用 openstreetmap.fr 的省 / 国家摘录。
许可：ODbL（与 Overture 道路数据相同，需署名 © OpenStreetMap contributors）。

  python scripts/fetch_osm_addresses.py [--markets PT,CO,...] [--keep-pbf]

每条记录：street, number, unit, postcode, city, name, is_poi, lat, lng（门牌在节点上取节点坐标，在建筑轮廓上取轮廓中心）。
只保留落在市场试点范围里的记录。顺便把带编号的道路（ref=PR-25、N11、A40）存成 osm_road_refs.parquet。
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp.intl.markets import MARKETS  # noqa: E402

BBBIKE = "https://download.bbbike.org/osm/bbbike/{0}/{0}.osm.pbf"
OSMFR = "https://download.openstreetmap.fr/extracts/{0}-latest.osm.pbf"
SOURCES = {
    "AU": [BBBIKE.format("Sydney"), BBBIKE.format("Melbourne")], "NZ": [BBBIKE.format("Auckland")],
    "IN": [BBBIKE.format("Bombay")], "CA": [BBBIKE.format("Toronto")], "MX": [BBBIKE.format("MexicoCity")],
    "PR": [OSMFR.format("central-america/puerto_rico")],
    "BR": [OSMFR.format("south-america/brazil/southeast/sao-paulo")], "AR": [BBBIKE.format("BuenosAires")],
    "CL": [BBBIKE.format("Santiago")], "CO": [BBBIKE.format("Bogota")], "GB": [BBBIKE.format("London")],
    "IE": [BBBIKE.format("Dublin")], "DE": [BBBIKE.format("Berlin")], "FR": [BBBIKE.format("Paris")],
    "NL": [BBBIKE.format("Amsterdam")], "BE": [BBBIKE.format("Bruessel")], "LU": [OSMFR.format("europe/luxembourg")],
    "CH": [BBBIKE.format("Zuerich")], "AT": [BBBIKE.format("Wien")], "IT": [OSMFR.format("europe/italy/lombardia")],
    "ES": [BBBIKE.format("Madrid")], "PT": [BBBIKE.format("Lisbon")], "DK": [BBBIKE.format("Copenhagen")],
    "SE": [BBBIKE.format("Stockholm")], "NO": [BBBIKE.format("Oslo")], "FI": [BBBIKE.format("Helsinki")],
    "EE": [BBBIKE.format("Tallinn")], "LV": [BBBIKE.format("Riga")], "PL": [BBBIKE.format("Warsaw")],
    "CZ": [BBBIKE.format("Prag")], "SK": [OSMFR.format("europe/slovakia/bratislavsky")],
    "HU": [BBBIKE.format("Budapest")], "SI": [BBBIKE.format("Ljubljana")], "HR": [BBBIKE.format("Zagreb")],
    "BG": [BBBIKE.format("Sofia")], "MY": [OSMFR.format("asia/malaysia")], "TH": [BBBIKE.format("Bangkok")],
    "VN": [BBBIKE.format("Saigon")], "ID": [OSMFR.format("asia/indonesia/jakarta")],
    "PH": [OSMFR.format("asia/philippines/metro_manila")], "AE": [OSMFR.format("asia/united_arab_emirates")],
    "SA": [OSMFR.format("asia/saudi_arabia")],
}
POI_KEYS = ("shop", "amenity", "office", "tourism", "craft", "leisure", "healthcare", "club")


def _download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    tmp = dest.with_suffix(".part")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            tmp.rename(dest)
            return
        except OSError:
            if attempt == 3:
                raise
            time.sleep(2 ** (attempt + 1))


def extract(pbf: Path, boxes: list[tuple[float, float, float, float]], refs: list | None = None) -> list[dict]:
    """返回门牌记录；refs 不为 None 时顺便收集带编号的道路（ref=PR-25、N11、A40）：[{ref, name, points}]。"""
    import osmium

    def inside(lat: float, lng: float) -> bool:
        return any(b[0] <= lng <= b[2] and b[1] <= lat <= b[3] for b in boxes)

    out = []
    fp = osmium.FileProcessor(str(pbf), osmium.osm.NODE | osmium.osm.WAY).with_locations()
    for o in fp:
        tags = o.tags
        if refs is not None and not o.is_node() and "highway" in tags and "ref" in tags:
            pts = [(n.location.lat, n.location.lon) for n in o.nodes if n.location.valid()]
            if pts and any(inside(*pt) for pt in pts):
                refs.append({"ref": tags.get("ref"), "name": tags.get("name") or "", "osm_id": f"w{o.id}",
                             "lats": [x[0] for x in pts], "lngs": [x[1] for x in pts]})
        if "addr:housenumber" not in tags:
            continue
        street = tags.get("addr:street") or ""
        if not street:
            continue
        if o.is_node():
            if not o.location.valid():
                continue
            lat, lng = o.location.lat, o.location.lon
        else:
            locs = [n.location for n in o.nodes if n.location.valid()]
            if not locs:
                continue
            lat = sum(x.lat for x in locs) / len(locs)
            lng = sum(x.lon for x in locs) / len(locs)
        if not inside(lat, lng):
            continue
        out.append({"street": street, "number": tags.get("addr:housenumber"),
                    "unit": tags.get("addr:unit") or tags.get("addr:flats") or "",
                    "postcode": tags.get("addr:postcode") or "", "city": tags.get("addr:city") or "",
                    "name": tags.get("name") or "", "is_poi": any(k in tags for k in POI_KEYS),
                    "osm_id": f"{'n' if o.is_node() else 'w'}{o.id}", "lat": lat, "lng": lng})
    return out


def main() -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", default=",".join(SOURCES))
    ap.add_argument("--keep-pbf", action="store_true")
    args = ap.parse_args()
    if Path("/root/.ccr/ca-bundle.crt").exists():
        os.environ.setdefault("SSL_CERT_FILE", "/root/.ccr/ca-bundle.crt")
    cache = ROOT / "data" / "osm"
    cache.mkdir(parents=True, exist_ok=True)
    for code in args.markets.split(","):
        m = MARKETS[code]
        boxes = [b for _, b in m.regions]
        t = time.time()
        rows, refs = [], []
        for url in SOURCES[code]:
            pbf = cache / url.rsplit("/", 1)[1]
            _download(url, pbf)
            rows += extract(pbf, boxes, refs)
            if not args.keep_pbf:
                pbf.unlink()
        if refs:  # 带编号的道路：参考库构建时给道路加编号别名（PR-25 = Avenida Juan Ponce de León）
            pq.write_table(pa.Table.from_pylist(refs), ROOT / "data" / "markets" / code / "osm_road_refs.parquet")
        seen, uniq = set(), []
        for r in rows:  # 两个摘录重叠的部分只留一份
            if r["osm_id"] not in seen:
                seen.add(r["osm_id"])
                uniq.append(r)
        pq.write_table(pa.Table.from_pylist(uniq), ROOT / "data" / "markets" / code / "osm_addresses.parquet")
        print(f"{code} OSM 门牌 {len(uniq):,} 条（{time.time() - t:.0f}s）", flush=True)


if __name__ == "__main__":
    main()
