"""线上真实流量上与 Google 的实测对照：Google 跑过的查询，我们的服务也跑一遍，按国家看。

数据是 1,000 条线上查询，Google 的返回来自公司线上评测（我们没有调用 Google），判对 854 条。
只有 Google 判对的 851 条有标准答案（库内目标门址坐标），所以逐国比的是"Google 做对的地址里，我们也做对多少"，
口径偏向 Google；按 1,000 条算时，Google 判错的 146 条记我们全错，我们的数字只会被低估。
输入是 geo_real_eval.py 的汇总（reports/geo_real_eval.json），不需要原始数据。

  python scripts/google_real_compare.py --report reports/geo_real_eval.json --out reports/google_real_compare.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from avmvp.intl.markets import MARKETS  # noqa: E402

GOOGLE_OK, TOTAL = 854, 1000
NEW5 = {"KW", "BH", "EG", "KZ", "DO"}  # 第二批市场，没有开放门牌数据（13 文档第 2.2 节）
GROUPS = (  # (分组名, 逐国表里的简称, 归属)
    ("有官方门址数据", "官方门址", lambda k: k in MARKETS and MARKETS[k].cls == "A"),
    ("没有官方门址表（英国、东南亚）", "无官方表", lambda k: k in MARKETS and MARKETS[k].cls == "C" and k not in NEW5),
    ("没有开放门牌数据（中东、哈萨克斯坦、多米尼加）", "无门牌数据", lambda k: k in MARKETS and (MARKETS[k].cls == "B" or k in NEW5)),
    # 新加坡引擎没接进 geo_real_eval，新加坡的 5 条也走这条路
    ("只核对 geo，没接参考库（含新加坡 5 条）", "只核对 geo", lambda k: k not in MARKETS),
)
# 没做对的原因，按 geo 返回的情况分（geo_real_eval 的 detail 键：geo 情况|我们的结论|最终位置）
NAMES = {"SG": "新加坡", "TR": "土耳其", "OM": "阿曼", "PE": "秘鲁", "QA": "卡塔尔", "UZ": "乌兹别克斯坦", "ZA": "南非"}
CAUSES = (("bad", "geo 错，我们没纠正过来"), ("near", "geo 偏 100–500 米"), ("ok", "geo 对，被我们判掉"),
          ("empty", "geo 没结果，我们也没给对"))
CAUSE_COLS = ("没做对：geo 错没纠正", "geo 偏 100–500 米", "geo 对被判掉", "geo 没结果")


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.1f}%" if b else "—"


def ok(v: dict) -> int:
    return v["accept_ok"] + v["confirm_ok"]


def causes(v: dict) -> Counter:
    out = Counter()
    for key, n in v["detail"].items():
        geo, action, final = key.split("|")
        if not (action in ("ACCEPT", "CONFIRM") and final == "ok"):
            out[geo] += n
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="reports/geo_real_eval.json")
    ap.add_argument("--out", default="reports/google_real_compare.md")
    args = ap.parse_args()
    report = json.load(open(args.report, encoding="utf-8"))
    countries = report["countries"]
    group_of = {k: (name, short) for k in countries for name, short, pred in GROUPS if pred(k)}
    if len(group_of) != len(countries):
        sys.exit("有国家没归到任何分组")
    n = sum(v["n"] for v in countries.values())
    got = sum(ok(v) for v in countries.values())
    acc = sum(v["accept"] for v in countries.values())
    acc_bad = sum(v["accept_bad"] for v in countries.values())
    geo = sum(v["geo_ok"] for v in countries.values())
    geo_bad = sum(v["geo_bad"] for v in countries.values())
    md = ["# 线上真实流量：与 Google 的实测对照", "",
          f"{TOTAL:,} 条线上查询，Google 的返回来自公司线上评测（没有调用 Google），判对 {GOOGLE_OK} 条。"
          f"其中 {n} 条有标准答案（库内目标门址坐标），都是 Google 做对的；这 {n} 条我们的服务也跑了一遍。"
          "我们的服务 = 收到 geo 的结果，用核对层判它能不能用，不能用时本引擎兜底。"
          "做对 = 直接通过或请用户确认、且位置离目标 ≤ 100 米。", "",
          "| 口径 | 条数 | Google | 我们的服务 | 只用现有 geo |", "|---|---|---|---|---|",
          f"| Google 做对的查询 | {n} | {n}（100%） | {got}（{pct(got, n)}） | {geo}（{pct(geo, n)}） |",
          f"| 全部查询（Google 做错的 {TOTAL - GOOGLE_OK} 条没有标准答案，记我们全错） | {TOTAL:,} | {GOOGLE_OK}（{pct(GOOGLE_OK, TOTAL)}） | "
          f"{got}（{pct(got, TOTAL)}） | {geo}（{pct(geo, TOTAL)}） |", "",
          f"我们直接通过 {acc} 条，其中错 {acc_bad} 条（{pct(acc_bad, acc)}）；只用现有 geo 时有结果就采用，"
          f"其中偏 500 米以上的错地址 {geo_bad} 条（{pct(geo_bad, n)}）。", "",
          "## 按数据条件分组", "",
          "| 分组 | Google 做对 | 我们也做对 | 只用现有 geo | 占我们没做对的 |", "|---|---|---|---|---|"]
    fails = n - got
    for name, _, _ in GROUPS:
        ks = [k for k in countries if group_of[k][0] == name]
        gn, gg, ge = (sum(countries[k][f] for k in ks) for f in ("n", "accept_ok", "geo_ok"))
        gg += sum(countries[k]["confirm_ok"] for k in ks)
        md.append(f"| {name} | {gn} | {gg}（{pct(gg, gn)}） | {pct(ge, gn)} | {gn - gg}（{pct(gn - gg, fails)}） |")
    md += ["", "## 按国家", "",
           "| 国家 | 数据条件 | Google 做对 | 我们也做对 | 只用现有 geo | 我们直接通过 | 其中错 | " + " | ".join(CAUSE_COLS) + " |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    total_causes = Counter()
    for k in sorted(countries, key=lambda k: (-ok(countries[k]) / countries[k]["n"], -countries[k]["n"])):
        v = countries[k]
        cs = causes(v)
        total_causes += cs
        name = MARKETS[k].name if k in MARKETS else NAMES.get(k, k)
        md.append(f"| {name}（{k}） | {group_of[k][1]} | {v['n']} | {ok(v)}（{pct(ok(v), v['n'])}） | "
                  f"{pct(v['geo_ok'], v['n'])} | {v['accept']} | {v['accept_bad']} | "
                  + " | ".join(str(cs[c]) for c, _ in CAUSES) + " |")
    rec = report["failure_buckets"]["recoverable"]
    md += ["", f"我们没做对的 {fails} 条，按 geo 的情况分：" + "；".join(f"{label} {total_causes[c]}" for c, label in CAUSES) + "。"
           f"按正确答案在不在我们手里分：{fails - rec} 条不在（缺门牌数据、缺更准的坐标），{rec} 条在手里但没选对"
           "（核对层判掉对的 geo，或本引擎对了却没选它），换更强的判断模型最多救回这些，见 [geo 真实返回评测](geo_real_eval.md) 最后一节。"]
    Path(args.out).write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
