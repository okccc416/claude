"""目标市场的地址"规则程度"画像：各国有没有开放的官方地址表、真实人写地址长什么样。

数据：Overture Maps（2026-09-23.1）
  - addresses 主题：各国开放官方地址表的覆盖情况（按 Parquet 统计信息计数，不下载数据）
  - places 主题：各城市商户自填地址（按城市范围读取），统计邮编、门牌、非拉丁文字、地标式描述等

  python scripts/profile_countries.py
输出：reports/country_address_profile.md、reports/country_address_profile.json
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import Counter
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.fs as pafs
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "2026-09-23.1"
# 市场 -> [(国家代码, 城市, 经纬度范围 xmin, ymin, xmax, ymax)]
CITIES = {
    "澳新": [("AU", "悉尼", (150.9, -34.1, 151.35, -33.7)), ("AU", "墨尔本", (144.8, -37.95, 145.2, -37.65)),
           ("NZ", "奥克兰", (174.65, -36.95, 174.9, -36.8))],
    "中东": [("AE", "迪拜", (55.1, 25.0, 55.45, 25.35)), ("SA", "利雅得", (46.55, 24.55, 46.85, 24.85)),
           ("QA", "多哈", (51.4, 25.2, 51.6, 25.4)), ("KW", "科威特城", (47.9, 29.25, 48.1, 29.4))],
    "东南亚": [("SG", "新加坡", (103.6, 1.22, 104.05, 1.47)), ("MY", "吉隆坡", (101.6, 3.05, 101.75, 3.2)),
            ("ID", "雅加达", (106.75, -6.3, 106.9, -6.12)), ("TH", "曼谷", (100.45, 13.68, 100.65, 13.82)),
            ("VN", "胡志明市", (106.62, 10.72, 106.75, 10.84)), ("PH", "马尼拉", (120.97, 14.52, 121.07, 14.62))],
    "欧洲": [("GB", "伦敦", (-0.2, 51.46, 0.0, 51.56)), ("DE", "柏林", (13.3, 52.47, 13.47, 52.56)),
           ("FR", "巴黎", (2.28, 48.83, 2.41, 48.9)), ("NL", "阿姆斯特丹", (4.84, 52.34, 4.95, 52.4))],
}
NON_LATIN = {"阿拉伯文": r"[؀-ۿ]", "泰文": r"[฀-๿]", "中日韩文字": r"[㐀-鿿]"}
VI_DIACRITICS = r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]"
# 地标 / 相对位置式描述（英、阿、马来 / 印尼、泰、越）
LANDMARK = re.compile(
    r"\b(?:near|opp|opposite|behind|next to|beside|in front of|dekat|samping|sebelah|depan|belakang|seberang|"
    r"gần|đối diện|cạnh|sau|trước)\b|بجانب|خلف|قرب|مقابل|أمام|ใกล้|ตรงข้าม|ข้าง", re.I)
UNIT = re.compile(r"#\s*\d|\b(?:unit|apt|suite|flat|level|floor|lantai|tầng|ชั้น)\b|الطابق|شقة", re.I)


def fs_s3() -> pafs.S3FileSystem:
    if Path("/root/.ccr/ca-bundle.crt").exists():
        os.environ.setdefault("AWS_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
    return pafs.S3FileSystem(anonymous=True, region="us-west-2")


def official_coverage(fs) -> Counter:
    """addresses 主题里每个国家的地址条数（只读 Parquet 文件尾的统计信息）。"""
    d = ds.dataset(f"overturemaps-us-west-2/release/{RELEASE}/theme=addresses/type=address/", filesystem=fs,
                   format="parquet")
    cnt: Counter = Counter()
    for f in d.files:
        md = pq.ParquetFile(fs.open_input_file(f)).metadata
        ci = [md.schema.column(i).path for i in range(md.num_columns)].index("country")
        for g in range(md.num_row_groups):
            st = md.row_group(g).column(ci).statistics
            if st is not None and st.has_min_max:
                if st.min == st.max:
                    cnt[st.min] += md.row_group(g).num_rows
                else:  # 跨国家的数据块：两端国家都算"有覆盖"
                    cnt[st.min] += 0
                    cnt[st.max] += 0
    return cnt


def profile_city(fs, bbox) -> dict:
    d = ds.dataset(f"overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/", filesystem=fs,
                   format="parquet")
    xmin, ymin, xmax, ymax = bbox
    inside = ((pc.field("bbox", "xmin") > xmin) & (pc.field("bbox", "xmax") < xmax)
              & (pc.field("bbox", "ymin") > ymin) & (pc.field("bbox", "ymax") < ymax))
    rows = d.to_table(filter=inside, columns=["addresses"]).to_pylist()
    addrs = [(r["addresses"] or [{}])[0] for r in rows]
    ff = [(a.get("freeform") or "").strip() for a in addrs]
    with_ff = [(f, a) for f, a in zip(ff, addrs) if f]
    n = max(len(with_ff), 1)
    rate = lambda pred: sum(1 for f, a in with_ff if pred(f, a)) / n  # noqa: E731
    out = {
        "places": len(rows),
        "with_address": len(with_ff) / max(len(rows), 1),
        "postcode": rate(lambda f, a: bool((a.get("postcode") or "").strip())),
        "house_number": rate(lambda f, a: bool(re.search(r"(?<![\d.])\d{1,5}[A-Za-z]?(?![\d.])", f))),
        "unit": rate(lambda f, a: bool(UNIT.search(f))),
        "landmark": rate(lambda f, a: bool(LANDMARK.search(f))),
        "tokens": sum(len(f.split()) for f, _ in with_ff) / n,
        "越南语声调符号": rate(lambda f, a: bool(re.search(VI_DIACRITICS, f.lower()))),
    }
    for name, rx in NON_LATIN.items():
        out[name] = rate(lambda f, a, rx=rx: bool(re.search(rx, f)))
    out["examples"] = [f for f, _ in with_ff[:: max(len(with_ff) // 6, 1)][:6]]
    return out


def main() -> None:
    t = time.time()
    fs = fs_s3()
    cov = official_coverage(fs)
    result = {"coverage": {}, "cities": {}}
    for market, cities in CITIES.items():
        for cc, city, bbox in cities:
            result["coverage"][cc] = cov.get(cc)
            result["cities"][f"{cc}·{city}"] = {"market": market, **profile_city(fs, bbox)}
            print(f"{market} {cc} {city}: {result['cities'][f'{cc}·{city}']['places']:,} 家商户（{time.time() - t:.0f}s）")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "country_address_profile.json").write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                                                     encoding="utf-8")
    pct = lambda x: f"{100 * x:.0f}%"  # noqa: E731
    L = ["# 目标市场地址画像（自动生成）\n",
         f"- 数据：Overture Maps {RELEASE}；官方地址表覆盖取自 addresses 主题，写法统计取自各城市商户自填地址（places 主题）",
         "- \"开放官方地址表\"= Overture addresses 主题收录的国家级地址数据（多来自各国政府开放数据，经 OpenAddresses 等发布）；"
         "未收录不代表该国没有地址数据，只是没有可自由使用的版本\n",
         "| 市场 | 城市 | 开放官方地址表（条） | 商户数 | 带邮编 | 含门牌数字 | 带单元 / 楼层 | 地标式描述 | 非拉丁文字 | 平均词数 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for key, c in result["cities"].items():
        cc, city = key.split("·")
        covn = result["coverage"].get(cc)
        cov_txt = f"{covn:,}" if covn else ("有（跨国数据块）" if covn == 0 else "无")
        script = max(((k, c[k]) for k in list(NON_LATIN) + ["越南语声调符号"]), key=lambda kv: kv[1])
        script_txt = f"{script[0]} {pct(script[1])}" if script[1] >= 0.01 else "—"
        L.append(f"| {c['market']} | {city}（{cc}） | {cov_txt} | {c['places']:,} | {pct(c['postcode'])} | "
                 f"{pct(c['house_number'])} | {pct(c['unit'])} | {pct(c['landmark'])} | {script_txt} | {c['tokens']:.1f} |")
    L.append("\n## 各城市地址样例\n")
    for key, c in result["cities"].items():
        L.append(f"- **{key}**：" + " ／ ".join(f"`{e[:70]}`" for e in c["examples"]))
    (ROOT / "reports" / "country_address_profile.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
