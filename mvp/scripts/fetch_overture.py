"""下载 Overture Maps 的新加坡数据到 data/overture/（只读取新加坡范围内的数据块，约 1 分钟）。

  - sg_address.parquet：addresses 主题，来源 OpenAddresses sg/countrywide = OneMap 地址表（2026 年快照），
    许可：Singapore Open Data Licence（需署名 Singapore Land Authority）
  - sg_places.parquet：places 主题里的新加坡商户（名称、类别、商户自填地址），许可：CDLA-Permissive-2.0

直接用 pyarrow 匿名读取 Overture 的公开 S3（不依赖 overturemaps 命令行，后者要访问 STAC 目录服务）。

  python scripts/fetch_overture.py [--release 2026-09-23.1]
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.fs as pafs
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
BBOX = (103.59, 1.15, 104.10, 1.48)  # 新加坡本岛及离岛（会带进一点柔佛 / 廖内，后续按国家 / 邮编过滤）
THEMES = {
    "sg_address.parquet": ("addresses", "address", None),
    "sg_places.parquet": ("places", "place", ["id", "names", "categories", "confidence", "addresses", "sources",
                                              "bbox", "operating_status", "basic_category"]),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", default="2026-09-23.1")
    args = ap.parse_args()
    if Path("/root/.ccr/ca-bundle.crt").exists():  # 走代理的环境需要指定证书
        os.environ.setdefault("AWS_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
    fs = pafs.S3FileSystem(anonymous=True, region="us-west-2")
    out_dir = ROOT / "data" / "overture"
    out_dir.mkdir(parents=True, exist_ok=True)
    xmin, ymin, xmax, ymax = BBOX
    inside = ((pc.field("bbox", "xmin") > xmin) & (pc.field("bbox", "xmax") < xmax)
              & (pc.field("bbox", "ymin") > ymin) & (pc.field("bbox", "ymax") < ymax))
    for name, (theme, typ, cols) in THEMES.items():
        t = time.time()
        d = ds.dataset(f"overturemaps-us-west-2/release/{args.release}/theme={theme}/type={typ}/", filesystem=fs,
                       format="parquet")
        cols = cols or [c for c in d.schema.names if c != "geometry"]
        table = d.to_table(filter=inside, columns=[c for c in cols if c in d.schema.names])
        pq.write_table(table, out_dir / name)
        print(f"{name}: {table.num_rows:,} 行（{time.time() - t:.0f}s）")


if __name__ == "__main__":
    main()
