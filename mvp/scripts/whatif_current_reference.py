"""如果把参考库从 2017 年换成 2026 年的官方地址表，同一个测试集上会有什么变化？

两份参考库都是 OneMap 地址数据（Singapore Open Data Licence），只是时间不同。
按"楼栋 + 道路 + 邮编"与测试集的真实地址比较（不依赖参考库编号），分别统计找对、误拒、错误建议、静默错误。

  python scripts/whatif_current_reference.py [--testset labeled/testset_sg_research_v1.csv]
输出：reports/whatif_current_reference.md
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from avmvp import ReferenceDB, Validator  # noqa: E402
from avmvp.normalize import match_key  # noqa: E402
from avmvp.validator import ACCEPT, ADD_SUB  # noqa: E402
from make_research_testset import load_current_db  # noqa: E402


def judge(res, truth) -> str:
    if truth is None:
        return "正确拒绝" if res.entity is None else "错误建议" if res.action not in (ACCEPT, ADD_SUB) else "静默错误"
    if res.entity is None:
        return "判 FIX"
    if (res.entity.blk, res.entity.road_key, res.entity.postal) == truth:
        return "找对 · 直接通过" if res.action in (ACCEPT, ADD_SUB) else "找对 · 要求确认"
    return "静默错误" if res.action in (ACCEPT, ADD_SUB) else "错误建议"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--testset", default=str(ROOT / "labeled" / "testset_sg_research_v1.csv"))
    ap.add_argument("--current", default=str(ROOT / "data" / "overture" / "sg_address.parquet"))
    args = ap.parse_args()
    with open(args.testset, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    refs = {"2017 参考库（当前）": ReferenceDB.load(ROOT / "data" / "reference_sg.csv.gz"),
            "2026 官方地址表": load_current_db(Path(args.current))}
    order = ["找对 · 直接通过", "找对 · 要求确认", "判 FIX", "正确拒绝", "错误建议", "静默错误"]
    groups = {"全部": lambda r: True, "参考库（2017）没有的新地址": lambda r: r["text_resolution"] == "NOT_IN_REFERENCE",
              "其余": lambda r: r["text_resolution"] != "NOT_IN_REFERENCE"}
    stats = {}
    for name, db in refs.items():
        v = Validator(db)
        out = []
        for r in rows:
            truth = (r["truth_blk"], match_key(r["truth_street"]), r["truth_postal"]) if r["truth_blk"] else None
            out.append((r, judge(v.validate(r["input"]), truth)))
        stats[name] = {g: Counter(j for r, j in out if pred(r)) for g, pred in groups.items()}
    L = ["# 参考库换成 2026 年数据的效果（自动生成）\n",
         f"- 测试集：`{Path(args.testset).name}`，{len(rows):,} 条；真实地址取自 2026 年官方地址表",
         f"- 2017 参考库 {len(refs['2017 参考库（当前）'].entities):,} 个地址；"
         f"2026 官方地址表 {len(refs['2026 官方地址表'].entities):,} 个地址\n"]
    for g in groups:
        n = sum(stats["2017 参考库（当前）"][g].values())
        L += [f"## {g}（{n:,} 条）\n", "| 结果 | " + " | ".join(refs) + " |", "|---|" + "---|" * len(refs)]
        for o in order:
            L.append(f"| {o} | " + " | ".join(f"{100 * stats[k][g][o] / max(n, 1):.1f}%" for k in refs) + " |")
        L.append("")
    insufficient = sum(1 for r in rows if r["text_resolution"] in ("AMBIGUOUS", "CONFLICTING"))
    L.append("说明：没有真实地址的条目（非新加坡、没有地址）判 FIX 记为\"正确拒绝\"。\"判 FIX\"里包含文字本身不足以确定地址的条目"
             f"（有歧义 / 字段矛盾，共 {insufficient} 条，占 {100 * insufficient / len(rows):.1f}%），这部分判 FIX 是对的。"
             "换库后，原来参考库里没有的新地址变得可以查到，同时参考库里被拆除 / 改名的旧地址不再会被选中。")
    (ROOT / "reports" / "whatif_current_reference.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
