"""多市场置信度：在开发集真实地址上统计各类结论"位置给对"的比例，在测试集上检验校准。

  python scripts/fit_intl_confidence.py [--jobs 3]
输出：models/confidence_intl.json、reports/intl_confidence_report.md
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from avmvp.intl.confidence import IntlConfidence, signatures  # noqa: E402
from avmvp.intl.engine import ACCEPT, ADD_SUB, FIX, Engine  # noqa: E402
from avmvp.intl.markets import MARKETS  # noqa: E402
from evaluate_markets import error_m, judge_real, real_cases  # noqa: E402

OK = ("正确·直接通过", "正确·要求确认", "判 FIX·片区对")


def collect(code: str, n_dev: int, n_test: int) -> dict:
    eng = Engine(code, "hybrid")
    cls = MARKETS[code].cls
    out = {}
    for split, n in (("dev", n_dev), ("test", n_test)):
        rows = []
        for c in real_cases(code, n, split):
            res = eng.validate(c["input"])
            ok = judge_real(eng, res, c) in OK
            err = error_m(eng, res, c)
            rows.append((signatures(res, code, cls), ok, res.action, res.lat is not None,
                         not ok and err is not None and err > 1000))
        out[split] = rows
    print(f"{code} done", flush=True)
    return out


def auroc(scores: list[float], labels: list[bool]) -> float:
    """按秩计算（Mann–Whitney U），并列取平均秩；45 个市场的样本量下逐对比较太慢。"""
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if not n_pos or not n_neg:
        return float("nan")
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    rank_pos = sum(r for r, y in zip(ranks, labels) if y)
    return (rank_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--n-dev", type=int, default=600)
    ap.add_argument("--n-test", type=int, default=1000)
    args = ap.parse_args()
    codes = list(MARKETS)
    if args.jobs > 1:
        from multiprocessing import Pool
        with Pool(args.jobs) as pool:
            data = dict(zip(codes, pool.starmap(collect, [(c, args.n_dev, args.n_test) for c in codes])))
    else:
        data = {c: collect(c, args.n_dev, args.n_test) for c in codes}

    model = IntlConfidence().fit((sigs, ok) for c in codes for sigs, ok, _, has_loc, _ in data[c]["dev"] if has_loc)
    model.save(ROOT / "models" / "confidence_intl.json")

    pct = lambda x: f"{100 * x:.1f}%"  # noqa: E731
    test = [(model.from_signatures(sigs), ok, act, MARKETS[c].cls, c, gross) for c in codes
            for sigs, ok, act, has_loc, gross in data[c]["test"] if has_loc]
    bins = [(0, .5), (.5, .7), (.7, .8), (.8, .9), (.9, .95), (.95, 1.01)]
    L = ["# 多市场置信度：校准检验（测试集，自动生成）\n",
         f"- 拟合：开发集真实地址（{len(codes)} 个市场 × {args.n_dev} 条）；检验：测试集真实地址（× {args.n_test} 条，开发阶段未看过）",
         "- 置信度 = 同类结论在开发集上\"位置给对\"的比例（四级签名逐级收缩，见 avmvp/intl/confidence.py）",
         f"- 只统计给出了位置的结论：{len(test):,} 条\n",
         "## 1. 可靠性（置信度说 x%，实际对了多少）\n", "| 置信度区间 | 条数 | 平均置信度 | 实际给对 |", "|---|---|---|---|"]
    ece = 0.0
    for lo, hi in bins:
        g = [(p, y) for p, y, *_ in test if lo <= p < hi]
        if not g:
            continue
        mp, acc = sum(p for p, _ in g) / len(g), sum(y for _, y in g) / len(g)
        ece += len(g) / len(test) * abs(mp - acc)
        L.append(f"| {lo:.2f}–{min(hi, 1):.2f} | {len(g):,} | {pct(mp)} | {pct(acc)} |")
    L += ["", f"期望校准误差（ECE）：**{pct(ece)}**；区分对错的能力（AUROC）：**{auroc([t[0] for t in test], [t[1] for t in test]):.3f}**\n"]
    L += ["## 2. 用置信度设门槛：自动通过多少、错多少\n",
          "规则：结论是 ACCEPT（含只提示补单元号）且置信度 ≥ 门槛才自动通过，其余请用户确认。"
          "错误率 = 自动通过里位置给错的比例（严格口径：门牌 ≤ 250 米、道路经过商户 250 米内，含商户坐标本身的误差）；"
          "\"偏差 >1 公里\"是商户坐标不准解释不了的错误。\n",
          "| 类别 | 门槛 | 自动通过占全部 | 自动通过里的错误率（严格） | 其中偏差 >1 公里 |", "|---|---|---|---|---|"]
    for cls in ("A", "B", "C"):
        g = [t for t in test if t[3] == cls]
        total = sum(len(data[c]["test"]) for c in codes if MARKETS[c].cls == cls)
        for th in (0.0, 0.8, 0.9, 0.95):
            acc = [t for t in g if t[2] in (ACCEPT, ADD_SUB) and t[0] >= th]
            err = sum(not t[1] for t in acc) / max(len(acc), 1)
            gross = sum(t[5] for t in acc) / max(len(acc), 1)
            L.append(f"| {cls} | {'不设' if th == 0 else f'≥ {th:.2f}'} | {pct(len(acc) / max(total, 1))} | {pct(err)} | "
                     f"{pct(gross)} |")
    L += ["", "## 3. 各市场（测试集）\n", "| 市场 | 平均置信度 | 实际给对 | AUROC |", "|---|---|---|---|"]
    for c in codes:
        g = [t for t in test if t[4] == c]
        if g:
            L.append(f"| {MARKETS[c].name}（{c}） | {pct(sum(t[0] for t in g) / len(g))} | {pct(sum(t[1] for t in g) / len(g))} | "
                     f"{auroc([t[0] for t in g], [t[1] for t in g]):.3f} |")
    (ROOT / "reports" / "intl_confidence_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
