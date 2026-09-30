"""下载各目标市场试点城市的 Overture Maps 数据到 data/markets/{国家代码}/：

  places.parquet          商户 / 楼宇 POI（名称、类别、商户自填地址、坐标）
  addresses.parquet       官方地址表（只有 A 类市场有）
  segments.parquet        有名称的道路（含多语种名称与线形，来自 OSM）
  divisions.parquet       行政区 / 片区（点，含多语种名称与上级）
  division_areas.parquet  行政区 / 片区边界（多边形，用于判断道路和 POI 属于哪个片区）

  python scripts/fetch_markets.py [--markets AU,DE,...] [--release 2026-09-23.1]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.fs as pafs
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp.intl.markets import MARKETS  # noqa: E402

AREA_SUBTYPES = ["county", "localadmin", "locality", "borough", "macrohood", "neighborhood", "microhood"]


def inside(b):
    xmin, ymin, xmax, ymax = b
    return ((pc.field("bbox", "xmin") > xmin) & (pc.field("bbox", "xmax") < xmax)
            & (pc.field("bbox", "ymin") > ymin) & (pc.field("bbox", "ymax") < ymax))


def overlaps(b):
    xmin, ymin, xmax, ymax = b
    return ((pc.field("bbox", "xmax") > xmin) & (pc.field("bbox", "xmin") < xmax)
            & (pc.field("bbox", "ymax") > ymin) & (pc.field("bbox", "ymin") < ymax))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", default=",".join(MARKETS))
    ap.add_argument("--release", default="2026-09-23.1")
    ap.add_argument("--only", help="只下载其中几类（逗号分隔，如 segments）")
    args = ap.parse_args()
    if Path("/root/.ccr/ca-bundle.crt").exists():
        os.environ.setdefault("AWS_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
    fs = pafs.S3FileSystem(anonymous=True, region="us-west-2")
    base = f"overturemaps-us-west-2/release/{args.release}/"
    sets = {
        "places": ("theme=places/type=place/", inside,
                   ["id", "names", "basic_category", "taxonomy", "confidence", "addresses", "bbox"], None),
        "addresses": ("theme=addresses/type=address/", inside, None, None),
        "segments": ("theme=transportation/type=segment/", inside, ["id", "names", "class", "geometry", "bbox"],
                     (pc.field("subtype") == "road") & pc.field("names", "primary").is_valid()),
        "divisions": ("theme=divisions/type=division/", inside,
                      ["id", "names", "subtype", "class", "local_type", "hierarchies", "parent_division_id", "country",
                       "admin_level", "population", "bbox"], None),
        "division_areas": ("theme=divisions/type=division_area/", overlaps,
                           ["id", "names", "subtype", "division_id", "country", "geometry", "bbox"],
                           pc.field("subtype").isin(AREA_SUBTYPES)),
    }
    datasets = {k: ds.dataset(base + p, filesystem=fs, format="parquet") for k, (p, *_) in sets.items()}
    for code in args.markets.split(","):
        m = MARKETS[code]
        out = ROOT / "data" / "markets" / code
        out.mkdir(parents=True, exist_ok=True)
        for name, (_, box, cols, extra) in sets.items():
            if args.only and name not in args.only.split(","):
                continue
            if name == "addresses" and m.cls != "A":
                continue
            t = time.time()
            d = datasets[name]
            use = [c for c in (cols or d.schema.names) if c in d.schema.names and (cols or c != "geometry")]
            tables = []
            for region, b in m.regions:
                f = box(b) if extra is None else box(b) & extra
                tb = d.to_table(filter=f, columns=use)
                tables.append(tb.append_column("region", pa.array([region] * tb.num_rows, pa.string())))
            table = pa.concat_tables(tables)
            if name in ("division_areas", "divisions"):  # 多个城市范围可能重复读到同一个片区
                ids = table.column("id").to_pylist()
                keep = [i for i, x in enumerate(ids) if x not in set(ids[:i])] if len(ids) < 50000 else None
                if keep is not None:
                    table = table.take(pa.array(keep))
            pq.write_table(table, out / f"{name}.parquet")
            print(f"{code} {name}: {table.num_rows:,} 行（{time.time() - t:.0f}s）", flush=True)


if __name__ == "__main__":
    main()
