"""试点范围守卫评测（avmvp/intl/coverage.py）。

1. 误判率：开发集（真实商户地址 + 合成地址，全部在试点范围内）有多少被判成"范围外"——应接近 0。
2. 线上查询（可选，--queries）：每行 {"regionCode": "DE", "input": "..."}，统计各市场被判范围内 / 范围外 / 无从判断的比例
   （报告里只写汇总数字，不写原文）。

  python scripts/coverage_eval.py [--markets DE,...] [--n-real 600] [--n-synth 300] [--queries path.jsonl] [--jobs 4]
输出：reports/coverage_guard.md、reports/coverage_guard.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from avmvp.intl.engine import Engine  # noqa: E402
from avmvp.intl.markets import MARKETS  # noqa: E402
from evaluate_markets import real_cases, synthetic_cases  # noqa: E402


def run_market(code: str, n_real: int, n_synth: int, queries: list[str]) -> tuple:
    eng = Engine(code, "hybrid")
    cases = [("real", c["input"]) for c in real_cases(code, n_real, "dev")] + \
            [("synth", c["input"]) for c in synthetic_cases(eng.ref, n_synth, "dev")]
    cnt: Counter = Counter()
    ex = []
    for kind, text in cases:
        cov = eng.validate(text).coverage
        cnt[(kind, cov.status)] += 1
        if cov.status == "OUTSIDE" and len(ex) < 5:
            ex.append({"input": text, "outside": cov.outside, "inside": cov.inside})
    row = {"real": sum(v for (k, _), v in cnt.items() if k == "real"),
           "synth": sum(v for (k, _), v in cnt.items() if k == "synth"),
           "real_outside": cnt[("real", "OUTSIDE")], "synth_outside": cnt[("synth", "OUTSIDE")],
           "real_inside": cnt[("real", "INSIDE")], "synth_inside": cnt[("synth", "INSIDE")]}
    live = None
    if queries:
        c2 = Counter(eng.validate(t).coverage.status for t in queries)
        live = dict(c2, total=len(queries))
    return code, row, ex, live


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", default=",".join(c for c in MARKETS if c != "SG"))
    ap.add_argument("--n-real", type=int, default=600)
    ap.add_argument("--n-synth", type=int, default=300)
    ap.add_argument("--queries")
    ap.add_argument("--jobs", type=int, default=1)
    args = ap.parse_args()
    queries = defaultdict(list)
    if args.queries:
        for line in open(args.queries, encoding="utf-8"):
            q = json.loads(line)
            queries[q["regionCode"]].append(q["input"])
    codes = args.markets.split(",")
    rows, examples, live = {}, {}, {}
    with ProcessPoolExecutor(args.jobs) as ex:
        futs = [ex.submit(run_market, c, args.n_real, args.n_synth, queries.get(c, [])) for c in codes]
        for f in futs:
            code, row, exs, lv = f.result()
            rows[code], examples[code] = row, exs
            if lv:
                live[code] = lv
            print(code, row, lv or "", flush=True)

    out = ROOT / "reports"
    json.dump({"dev": rows, "examples": examples, "queries": live}, open(out / "coverage_guard.json", "w"),
              ensure_ascii=False, indent=1)
    tr = sum(r["real"] for r in rows.values())
    ts = sum(r["synth"] for r in rows.values())
    fr = sum(r["real_outside"] for r in rows.values())
    fs = sum(r["synth_outside"] for r in rows.values())
    md = ["# 试点范围守卫评测", "",
          "开发集全部在试点范围内：被判成\"范围外\"的都是误判（应接近 0）。"
          "\"判范围内\"是找到了范围内证据（邮编 / 城镇 / 片区）的比例，其余是没有可用证据、照常匹配的。", "",
          f"合计：真实商户地址 {tr:,} 条误判 {fr}（{fr / max(tr, 1):.2%}），合成地址 {ts:,} 条误判 {fs}（{fs / max(ts, 1):.2%}）", "",
          "| 市场 | 真实地址 | 误判范围外 | 判范围内 | 合成地址 | 误判范围外 | 判范围内 |", "|---|---|---|---|---|---|---|"]
    for code, r in rows.items():
        md.append(f"| {code} | {r['real']} | {r['real_outside']} | {r['real_inside'] / max(r['real'], 1):.0%} | "
                  f"{r['synth']} | {r['synth_outside']} | {r['synth_inside'] / max(r['synth'], 1):.0%} |")
    if live:
        md += ["", "## 线上查询", "", "| 市场 | 条数 | 范围外 | 范围内 | 无从判断 |", "|---|---|---|---|---|"]
        for code, c in live.items():
            md.append(f"| {code} | {c['total']} | {c.get('OUTSIDE', 0)} | {c.get('INSIDE', 0)} | {c.get('UNKNOWN', 0)} |")
    md += ["", "## 误判样例（开发集）", ""]
    for code, ex in examples.items():
        for e in ex:
            md.append(f"- {code}：{e['input']} — 范围外证据 {', '.join(e['outside'])}；范围内 {', '.join(e['inside']) or '无'}")
    (out / "coverage_guard.md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
