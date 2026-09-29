"""下载 OneMap 新加坡邮编全量导出，聚合为地址参考库 data/reference_sg.csv.gz。

数据来源：https://github.com/xkjyeah/singapore-postal-codes （OneMap 邮编检索导出，2017 年起）
许可：Singapore Open Data Licence（https://www.onemap.gov.sg/legal/opendatalicence.html），使用需注明出处。
注意：该导出并非最新数据，生产环境应向 SLA / OneMap 获取最新授权数据。
"""

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from avmvp.reference import rows_from_onemap_dump, write_rows  # noqa: E402

URL = "https://raw.githubusercontent.com/xkjyeah/singapore-postal-codes/master/buildings.json"
ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
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
