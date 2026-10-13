"""全国门址库：下载一个国家全部的官方地址点（Overture addresses），存成 data/markets/<国家>/national.sqlite。

试点城市的参考库（道路、片区、POI、地址点）放在内存里，装不下整个国家；试点城市以外的地址原来只能给到城镇级
（范围守卫）。全国门址库只存门牌点、放在磁盘上，按"门牌 + 邮编""门牌 + 城镇"查，用来核对试点城市以外的地址
（avmvp/intl/national.py）。只下载需要的列（不要几何和来源），按行组的国家统计跳过别国数据。

  python scripts/fetch_national.py --markets NZ,AT,BE [--release 2026-09-23.1]
  python scripts/fetch_national.py --markets NZ --reindex   # 不重新下载，只按当前代码重算路名前缀、重建索引
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.fs as pafs
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp.intl.coverage import norm  # noqa: E402
from avmvp.intl.national import INDEXES, SCHEMA, name_prefix  # noqa: E402
from avmvp.intl.reference import DATA, address_numbers  # noqa: E402
from avmvp.intl.text import norm_postcode  # noqa: E402

COLS = ["street", "number", "unit", "postcode", "postal_city", "address_levels", "country", "bbox"]


def _vacuum(db: sqlite3.Connection, path: Path) -> None:
    """VACUUM 要临时多占一份文件大小的磁盘；空间不够就跳过（只是文件稍大，不影响查询）。"""
    if shutil.disk_usage(path.parent).free > 2.5 * path.stat().st_size:
        db.execute("VACUUM")
    else:
        print(f"磁盘空间不够，跳过 VACUUM：{path}", flush=True)


def row_groups(fs, base: str, cc: str):
    d = ds.dataset(base, filesystem=fs, format="parquet")
    for f in d.files:
        pf = pq.ParquetFile(f, filesystem=fs)
        md = pf.metadata
        ci = [i for i in range(md.num_columns) if md.schema.column(i).name == "country"][0]
        for r in range(md.num_row_groups):
            st = md.row_group(r).column(ci).statistics
            if st is None or (st.min <= cc <= st.max):
                yield pf, r


def fetch(cc: str, fs, base: str) -> None:
    out = DATA / cc / "national.sqlite"
    tmp = out.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    db.executescript(SCHEMA)
    n, t = 0, time.time()
    for pf, r in row_groups(fs, base, cc):
        tab = pf.read_row_group(r, columns=COLS)
        tab = tab.filter(pc.equal(tab["country"], cc))
        if not tab.num_rows:
            continue
        rows = []
        for x in tab.to_pylist():
            street, num = (x["street"] or "").strip(), (x["number"] or "").strip()
            if not street:
                continue
            levels = [lv["value"] for lv in (x["address_levels"] or []) if lv and lv.get("value")]
            loc = (x["postal_city"] or (levels[-1] if levels else "") or "").strip()
            b = x["bbox"]
            nkey = address_numbers(cc, num, x["unit"] or "")[1][0] if num else ""  # 与参考库同一套门牌写法（66 33 -> 66-33）
            rows.append((street, name_prefix(street), num, nkey, (x["unit"] or "").strip(),
                         norm_postcode(x["postcode"], cc) if x["postcode"] else "", loc, norm(loc),
                         levels[0] if levels else "", (b["ymin"] + b["ymax"]) / 2, (b["xmin"] + b["xmax"]) / 2))
        db.executemany("INSERT INTO addr(street, s3, number, nkey, unit, postcode, locality, lkey, region, lat, lng) "
                       "VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
        n += len(rows)
        print(f"{cc} {n:,} 条（{time.time() - t:.0f} 秒）", flush=True)
    for sql in INDEXES:
        db.execute(sql)
    db.commit()
    _vacuum(db, tmp)
    db.close()
    tmp.replace(out)
    print(f"{cc} 完成：{n:,} 条，{out.stat().st_size / 1e6:.0f} MB", flush=True)


def reindex(cc: str) -> None:
    path = DATA / cc / "national.sqlite"
    db = sqlite3.connect(path)
    db.create_function("name_prefix", 1, name_prefix, deterministic=True)
    for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL").fetchall():
        db.execute(f"DROP INDEX {name}")
    db.execute("UPDATE addr SET s3 = name_prefix(street)")
    for sql in INDEXES:
        db.execute(sql)
    db.commit()
    _vacuum(db, path)
    db.close()
    print(f"{cc} 已重建索引：{path.stat().st_size / 1e6:.0f} MB", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", required=True)
    ap.add_argument("--release", default="2026-09-23.1")
    ap.add_argument("--reindex", action="store_true", help="不下载，只重算已有 national.sqlite 的路名前缀和索引")
    args = ap.parse_args()
    if args.reindex:
        for cc in args.markets.split(","):
            reindex(cc)
        return
    if Path("/root/.ccr/ca-bundle.crt").exists():
        os.environ.setdefault("AWS_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
    fs = pafs.S3FileSystem(anonymous=True, region="us-west-2")
    base = f"overturemaps-us-west-2/release/{args.release}/theme=addresses/type=address/"
    for cc in args.markets.split(","):
        fetch(cc, fs, base)


if __name__ == "__main__":
    main()
