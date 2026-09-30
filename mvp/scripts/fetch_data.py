"""构建新加坡地址参考库。

默认：下载 OneMap 邮编全量导出（2017 年起），聚合为 data/reference_sg.csv.gz（历史评测用它，保证结果可复现）。
  数据来源：https://github.com/xkjyeah/singapore-postal-codes
--source overture：用 2026 年的 OneMap 地址快照（经 OpenAddresses / Overture 发布，先运行 scripts/fetch_overture.py）
  生成 data/reference_sg_2026.csv.gz。服务默认优先用这份（新楼盘齐全，见 docs/11）。
许可：Singapore Open Data Licence（https://www.onemap.gov.sg/legal/opendatalicence.html），需署名 Singapore Land Authority。
"""

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from avmvp.reference import rows_from_onemap_dump, write_rows  # noqa: E402

URL = "https://raw.githubusercontent.com/xkjyeah/singapore-postal-codes/master/buildings.json"
ROOT = Path(__file__).resolve().parents[1]


def from_overture() -> None:
    import pyarrow.parquet as pq
    src = ROOT / "data" / "overture" / "sg_address.parquet"
    records = [{"BLK_NO": str(r["number"] or ""), "ROAD_NAME": r["street"] or "", "POSTAL": r["postcode"] or "",
                "BUILDING": r["unit"] or "", "LATITUDE": r["bbox"]["ymin"], "LONGITUDE": r["bbox"]["xmin"]}
               for r in pq.read_table(src, columns=["number", "street", "unit", "postcode", "bbox"]).to_pylist()]
    rows = rows_from_onemap_dump(records)
    out = ROOT / "data" / "reference_sg_2026.csv.gz"
    write_rows(rows, out)
    print(f"2026 年快照 {len(records):,} 条 -> 地址实体 {len(rows):,} 个，已写入 {out}")


def main() -> None:
    if "--source" in sys.argv and sys.argv[sys.argv.index("--source") + 1] == "overture":
        return from_overture()
    raw_path = ROOT / "data" / "onemap_buildings.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if not raw_path.exists():
        print(f"下载 {URL} ...")
        urllib.request.urlretrieve(URL, raw_path)
    records = json.loads(raw_path.read_text(encoding="utf-8"))
    rows = rows_from_onemap_dump(records)
    out = ROOT / "data" / "reference_sg.csv.gz"
    write_rows(rows, out)
    print(f"原始记录 {len(records):,} 条 -> 地址实体 {len(rows):,} 个，已写入 {out}")


if __name__ == "__main__":
    main()
