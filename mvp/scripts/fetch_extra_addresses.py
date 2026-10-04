"""下载 Overture 之外的官方 / 开放地址数据，统一存成 data/markets/{国家代码}/extra_addresses.parquet
（字段与 Overture 地址表相同：number, street, unit, postcode, postal_city, bbox），构建参考库时与官方地址表合并。

来源（都是政府开放数据）：
  CO  波哥大地籍局 Placa Domiciliaria（门牌牌号，约 180 万个，CC-BY-4.0，每月更新）
      datosabiertos.bogota.gov.co/dataset/placa-domiciliaria：PDONVIAL = 道路（CL 153A / KR 7A），PDOTEXTO = 门牌（7 91 = # 7-91）
  BG  索非亚市政府开放数据 address_sofia（12.5 万个，CC-BY-4.0）：道路门牌，以及住宅小区的楼号
      （ж.к. Младост 1, бл. 12 -> 道路"ж.к. Младост 1"、门牌 12；入口记为单元）

试过但开发集上没有提升、默认不用的（--markets 显式指定才下载）：
  SE  斯德哥尔摩市地址点（2016，经 OpenAddresses 缓存）+ 纳卡市地址点：瑞典开发集定位对 93.0% -> 91.7%
  GB  Ordnance Survey Code-Point Open 邮编中心点（存成 extra_postcodes.parquet）：英国开发集 91.0% -> 91.2%

  python scripts/fetch_extra_addresses.py [--markets CO]
"""

from __future__ import annotations

import argparse
import io
import os
import sqlite3
import struct
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp.intl.markets import MARKETS  # noqa: E402

BOGOTA_PDOM = ("https://datosabiertos.bogota.gov.co/dataset/d4a31443-789c-478a-9db2-ff967e1d9a50/resource/"
               "d612e92f-1815-4db8-9756-23f877918c5f/download/pdom.gpkg.08.26.zip")


def _download(url: str) -> bytes:
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                return r.read()
        except OSError:
            if attempt == 3:
                raise
            time.sleep(2 ** (attempt + 1))
    return b""


def _gpkg_point(blob: bytes) -> tuple[float, float] | None:
    """GeoPackage 几何（GP 头 + WKB）-> (经度, 纬度)，只处理点。"""
    if not blob or blob[:2] != b"GP":
        return None
    flags = blob[3]
    env = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}.get((flags >> 1) & 0x07, 0)
    wkb = blob[8 + env:]
    order = "<" if wkb[0] == 1 else ">"
    gtype = struct.unpack(order + "I", wkb[1:5])[0] % 1000
    if gtype != 1:
        return None
    return struct.unpack(order + "dd", wkb[5:21])


def bogota(cache: Path) -> list[dict]:
    path = cache / "PDOM.gpkg"
    if not path.exists():
        zipfile.ZipFile(io.BytesIO(_download(BOGOTA_PDOM))).extractall(cache)
    db = sqlite3.connect(path)
    out = []
    for geom, number, street in db.execute("SELECT geom, PDOTEXTO, PDONVIAL FROM PDOM"):
        pt = _gpkg_point(geom)
        if not pt or not number or not street:
            continue
        lng, lat = pt
        out.append({"number": number.strip(), "street": street.strip(), "unit": "", "postcode": "", "postal_city": "Bogotá",
                    "bbox": {"xmin": lng, "xmax": lng, "ymin": lat, "ymax": lat}})
    return out


SOFIA = ("https://urbandata.sofia.bg/dataset/5dd1b862-7b4e-4fed-9061-96f1f1288c1e/resource/"
         "7b32c5f8-5f25-4b24-92f9-43e265275587/download/address_sofia.zip")
STOCKHOLM = "https://data.openaddresses.io/cache/uploads/migurski/d8b81c/stockholm20161206a.zip"
NACKA = ("https://karta.nacka.se/geoserver/wfs?SERVICE=WFS&version=1.1.0&request=GetFeature&typeName=nacka:adresspunkter"
         "&outputFormat=application%2Fjson&srsName=EPSG:4326")


def _row(street: str, number: str, lng: float, lat: float, unit: str = "", postcode: str = "", city: str = "") -> dict:
    return {"number": number.strip(), "street": street.strip(), "unit": unit, "postcode": postcode, "postal_city": city,
            "bbox": {"xmin": lng, "xmax": lng, "ymin": lat, "ymax": lat}}


def sofia(cache: Path) -> list[dict]:
    import json
    path = cache / "address_sofia.geojson"
    if not path.exists():
        zipfile.ZipFile(io.BytesIO(_download(SOFIA))).extractall(cache)
    out = []
    for f in json.loads(path.read_text(encoding="utf-8"))["features"]:
        q, (lng, lat) = f["properties"], f["geometry"]["coordinates"][:2]
        if q.get("block") and q.get("lareaunit"):  # 小区楼号：ж.к. Младост 1, бл. 12（也能只写 Младост 1 12）
            area = q["lareaunit"].strip()
            short = area.split(".", 2)[-1].strip() if area.lower().startswith(("ж.к.", "кв.")) else ""
            name = f"{area} ({short})" if short and len(short.split()) >= 1 and short != area else area
            out.append(_row(name, q["block"], lng, lat, unit=q.get("entrance") or "", city="София"))
        elif q.get("street") and q.get("streetnum"):
            out.append(_row(q["street"], q["streetnum"], lng, lat, unit=q.get("entrance") or "", city="София"))
    return out


def stockholm(cache: Path) -> list[dict]:
    import csv
    import json
    path = cache / "stockholm" / "addresses.csv"
    if not path.exists():
        zipfile.ZipFile(io.BytesIO(_download(STOCKHOLM))).extractall(cache / "stockholm")
    out = [_row(r["streetname"], r["streetnum"], float(r["lon"]), float(r["lat"]), postcode=r["postalcode"],
                city=r["postalarea"]) for r in csv.DictReader(open(path, encoding="utf-8")) if r["streetname"]]
    nacka = cache / "nacka.geojson"
    if not nacka.exists():
        nacka.write_bytes(_download(NACKA))
    for f in json.loads(nacka.read_text(encoding="utf-8"))["features"]:
        q = f["properties"]
        if q.get("adromrade") and q.get("adrplats") and f.get("geometry"):
            lng, lat = f["geometry"]["coordinates"][:2]
            out.append(_row(q["adromrade"].title(), q["adrplats"], lng, lat, city="Nacka"))
    return out


SOURCES = {"CO": bogota, "BG": sofia, "SE": stockholm}
DEFAULT = ("CO", "BG")  # 开发集上有提升的
CODEPOINT = "https://api.os.uk/downloads/v1/products/CodePointOpen/downloads?area=GB&format=CSV&redirect"


def codepoint(cache: Path) -> list[dict]:
    import csv
    from pyproj import Transformer
    folder = cache / "codepo"
    if not folder.exists():
        zipfile.ZipFile(io.BytesIO(_download(CODEPOINT))).extractall(folder)
    to_wgs = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
    out = []
    for f in sorted((folder / "Data" / "CSV").glob("*.csv")):
        for r in csv.reader(open(f, encoding="utf-8")):
            if len(r) < 4 or not r[2].isdigit() or r[2] == "0":
                continue
            lng, lat = to_wgs.transform(float(r[2]), float(r[3]))
            out.append({"postcode": r[0], "lat": lat, "lng": lng})
    return out


POSTCODE_SOURCES = {"GB": codepoint}


def main() -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", default=",".join(DEFAULT))
    args = ap.parse_args()
    if Path("/root/.ccr/ca-bundle.crt").exists():
        os.environ.setdefault("SSL_CERT_FILE", "/root/.ccr/ca-bundle.crt")
    cache = ROOT / "data" / "extra"
    cache.mkdir(parents=True, exist_ok=True)
    for code in args.markets.split(","):
        t = time.time()
        boxes = [b for _, b in MARKETS[code].regions]
        if code in POSTCODE_SOURCES:  # 邮编中心点：取试点范围外扩约 10 公里
            pcs = [r for r in POSTCODE_SOURCES[code](cache)
                   if any(b[0] - 0.15 <= r["lng"] <= b[2] + 0.15 and b[1] - 0.1 <= r["lat"] <= b[3] + 0.1 for b in boxes)]
            pq.write_table(pa.Table.from_pylist(pcs), ROOT / "data" / "markets" / code / "extra_postcodes.parquet")
            print(f"{code} 邮编中心点 {len(pcs):,} 个（{time.time() - t:.0f}s）", flush=True)
        if code not in SOURCES:
            continue
        rows = [r for r in SOURCES[code](cache)
                if any(b[0] <= r["bbox"]["xmin"] <= b[2] and b[1] <= r["bbox"]["ymin"] <= b[3] for b in boxes)]
        pq.write_table(pa.Table.from_pylist(rows), ROOT / "data" / "markets" / code / "extra_addresses.parquet")
        print(f"{code} 补充地址点 {len(rows):,} 条（{time.time() - t:.0f}s）", flush=True)


if __name__ == "__main__":
    main()
