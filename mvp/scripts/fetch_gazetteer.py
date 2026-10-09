"""全国地名 / 邮编表（GeoNames，CC BY 4.0）：判断输入写的地点在不在试点范围内（见 avmvp/intl/coverage.py）。

每个市场下载 GeoNames 的国家文件（居民点 + 各级行政区，含当地语言别名）和邮编文件，
精简后写到 data/markets/<市场>/gazetteer.json.gz：
  places    [名称列表, 纬度, 经度, 类别, 人口, 一级行政区代码]   类别：P 居民点 / X 城区片区 / A1 A2 A3 行政区
  postcodes [邮编, 地名, 纬度, 经度]

  python scripts/fetch_gazetteer.py [--markets DE,PL,...] [--cache 下载目录]
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import re
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp.intl.markets import MARKETS  # noqa: E402
from avmvp.intl.reference import DATA  # noqa: E402

DUMP = "https://download.geonames.org/export/dump/{cc}.zip"
ZIP = "https://download.geonames.org/export/zip/{cc}.zip"
KIND = {"ADM1": "A1", "ADM2": "A2", "ADM3": "A3", "PPLX": "X"}
SKIP_P = {"PPLH", "PPLQ", "PPLW", "PPLCH"}  # 历史上的 / 废弃的 / 已毁的居民点
# 各市场保留哪些文字的别名（GeoNames 别名混着几十种语言和机场代码，只留当地会写的）
SCRIPTS = {"SA": "ARAB", "AE": "ARAB", "TH": "THAI", "JP": "CJK", "BG": "CYRL"}
_LATIN = re.compile(r"^[A-Za-zÀ-ɏḀ-ỿ'’.\- ()/]+$")
_RANGES = {"ARAB": re.compile(r"^[؀-ۿݐ-ݿ\s'’.\-]+$"), "THAI": re.compile(r"^[฀-๿\s.\-]+$"),
           "CJK": re.compile(r"^[぀-ヿ一-鿿々ヶ\s]+$"), "CYRL": re.compile(r"^[Ѐ-ӿ\s'’.\-]+$")}


def fetch(url: str, path: Path) -> Path:
    if path.exists() and path.stat().st_size > 0:
        return path
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                path.write_bytes(r.read())
            return path
        except Exception as e:  # noqa: BLE001  网络抖动：退避重试
            if i == 3:
                raise
            print(f"  重试 {url}: {e}")
            time.sleep(2 ** (i + 1))
    return path


def keep_alt(name: str, market: str) -> bool:
    if len(name) < 3 or re.search(r"\d", name) or (name.isupper() and len(name) <= 4):  # 机场 / 车站代码
        return False
    script = SCRIPTS.get(market)
    return bool(_LATIN.match(name) or (script and _RANGES[script].match(name)))


def read_dump(path: Path, cc: str, market: str) -> list[list]:
    out = []
    with zipfile.ZipFile(path) as z, z.open(f"{cc}.txt") as f:
        for line in io.TextIOWrapper(f, encoding="utf-8"):
            c = line.rstrip("\n").split("\t")
            if len(c) < 15:
                continue
            fclass, fcode = c[6], c[7]
            if fclass == "P" and fcode not in SKIP_P:
                kind = KIND.get(fcode, "P")
            elif fclass == "A" and fcode in KIND:
                kind = KIND[fcode]
            else:
                continue
            names = [c[1]] + ([c[2]] if c[2] and c[2] != c[1] else [])
            for a in c[3].split(","):
                a = a.strip()
                if a and a not in names and keep_alt(a, market):
                    names.append(a)
            out.append([names, round(float(c[4]), 5), round(float(c[5]), 5), kind, int(c[14] or 0), c[10]])
    return out


def read_zip(path: Path, cc: str) -> list[list]:
    out = []
    with zipfile.ZipFile(path) as z, z.open(f"{cc}.txt") as f:
        for line in io.TextIOWrapper(f, encoding="utf-8"):
            c = line.rstrip("\n").split("\t")
            if len(c) >= 11 and c[9] and c[10]:
                out.append([c[1], c[2], round(float(c[9]), 5), round(float(c[10]), 5)])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", default=",".join(c for c in MARKETS if c != "SG"))
    ap.add_argument("--cache", default=str(DATA.parent / "geonames"))
    args = ap.parse_args()
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    for market in args.markets.split(","):
        cc = "GB" if market == "UK" else market
        places = read_dump(fetch(DUMP.format(cc=cc), cache / f"dump_{cc}.zip"), cc, market)
        try:
            pcs = read_zip(fetch(ZIP.format(cc=cc), cache / f"zip_{cc}.zip"), cc)
        except Exception as e:  # noqa: BLE001  部分国家没有邮编文件
            print(f"  {market} 没有邮编文件：{e}")
            pcs = []
        out = DATA / market / "gazetteer.json.gz"
        with gzip.open(out, "wt", encoding="utf-8") as f:
            json.dump({"source": "GeoNames (CC BY 4.0) https://www.geonames.org", "places": places,
                       "postcodes": pcs}, f, ensure_ascii=False)
        print(f"{market}: 地名 {len(places):,}，邮编 {len(pcs):,} -> {out}", flush=True)


if __name__ == "__main__":
    main()
