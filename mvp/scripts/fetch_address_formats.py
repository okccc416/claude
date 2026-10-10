"""下载 Google 的地址格式元数据（libaddressinput 用的 Address Data Service，Google Address Validation 的
"一个国家的地址该有哪些字段"即按这套规则），存成 avmvp/intl/address_formats.json 随代码提交（几十 KB）。

每个国家取：排版（fmt：%N 姓名 %O 公司 %A 街道行 %D 区 %C 城市 %S 州 / 省 %Z 邮编 %X 分拣码）、必填字段（require）、
邮编格式、州 / 省列表及其邮编前缀（sub_zips，用于从邮编补全州 / 省）。数据许可见 mvp/README.md。

  python scripts/fetch_address_formats.py [--countries AU,DE,...]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from avmvp.intl.markets import MARKETS  # noqa: E402

URL = "https://chromium-i18n.appspot.com/ssl-address/data/{cc}"
OUT = Path(__file__).resolve().parents[1] / "avmvp" / "intl" / "address_formats.json"
EXTRA = ("KW", "BH", "OM", "QA", "EG", "KZ", "UZ", "PE", "DO", "TR", "ZA", "SG", "US")
KEEP = ("name", "lang", "languages", "fmt", "lfmt", "require", "upper", "zip", "state_name_type",
        "locality_name_type", "sublocality_name_type", "zip_name_type", "sub_keys", "sub_names", "sub_lnames",
        "sub_zips", "sub_isoids")


def fetch(cc: str) -> dict:
    for attempt in range(4):
        try:
            with urllib.request.urlopen(URL.format(cc=cc), timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001  网络抖动：退避重试
            err = e
            time.sleep(2 ** (attempt + 1))
    raise SystemExit(f"{cc}: {err}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", default=",".join(list(MARKETS) + [c for c in EXTRA if c not in MARKETS]))
    args = ap.parse_args()
    zz = fetch("ZZ")  # 默认值：没写的字段按 ZZ
    out = {"source": URL.format(cc="<CC>"), "defaults": {k: zz[k] for k in ("fmt", "require", "upper") if k in zz},
           "countries": {}}
    for cc in args.countries.split(","):
        d = fetch(cc)
        out["countries"][cc] = {k: d[k] for k in KEEP if k in d}
        time.sleep(0.2)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT, len(out["countries"]))


if __name__ == "__main__":
    main()
