"""训练各市场的机器学习地址解析器（CRF）：用参考库里"训练部分"的道路按各市场写法渲染带标签样本。

  python scripts/train_market_parsers.py [--markets AU,...] [--n 20000]
输出：data/markets/{国家代码}/crf.model；reports/crf_training.md（逐词标签准确率，在测试部分道路的渲染样本上计算）
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp.intl.crf import CRFParser, features, train  # noqa: E402
from avmvp.intl.markets import MARKETS  # noqa: E402
from avmvp.intl.reference import MarketReference  # noqa: E402
from avmvp.intl.render import Renderer  # noqa: E402


def samples(ref, split, n, seed):
    rd = Renderer(ref, split, seed)
    out = []
    while len(out) < n:
        s = rd.sample(noise=0.35)
        if s is not None and s.tokens:
            out.append(s)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", default=",".join(MARKETS))
    ap.add_argument("--n", type=int, default=20000)
    args = ap.parse_args()
    L = ["# 机器学习解析器（CRF）训练结果（自动生成）\n",
         "逐词标签准确率：在\"测试部分\"道路（训练时没见过的道路名）渲染的 2,000 条样本上计算。\n",
         "| 市场 | 训练样本 | 训练耗时 | 逐词准确率 | 道路词召回 | 门牌召回 | 片区词召回 |", "|---|---|---|---|---|---|---|"]
    for code in args.markets.split(","):
        t = time.time()
        ref = MarketReference.load(code)
        train(ref, samples(ref, "train", args.n, 1), ref.dir / "crf.model")
        took = time.time() - t
        parser = CRFParser(ref)
        tot, ok, rec = 0, 0, Counter()
        for s in samples(ref, "test", 2000, 2):
            pred = parser.tagger.tag(features(s.tokens, s.seps, parser.vocab))
            for g, p in zip(s.labels, pred):
                tot += 1
                ok += g == p
                rec[(g, "n")] += 1
                rec[(g, "ok")] += g == p
        r = lambda lab: rec[(lab, "ok")] / max(rec[(lab, "n")], 1)  # noqa: E731
        L.append(f"| {MARKETS[code].name}（{code}） | {args.n:,} | {took:.0f}s | {100 * ok / tot:.1f}% | "
                 f"{100 * r('STREET'):.1f}% | {100 * r('NUM'):.1f}% | {100 * r('AREA'):.1f}% |")
        print(L[-1], flush=True)
    (ROOT / "reports" / "crf_training.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
