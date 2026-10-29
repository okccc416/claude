"""改动前后逐条对比：同一批开发集样本，用两份代码各跑一遍，列出结论变了的样本。

汇总数字（evaluate_markets.py）只能看出"多对了几条"，看不出是哪几条、为什么变。改了通用逻辑（全国门址库、噪声剥离、
解析）之后，用这个脚本把变了的样本逐条找出来看。

  # 1. 旧版本检出到 worktree，数据目录共用
  git worktree add ../av_before <旧提交>
  ln -s $PWD/data ../av_before/mvp/data
  # 2. 两边各导出一份逐条结论（同一套样本：开发集真实商户地址 + 合成地址）
  python scripts/regression_diff.py dump --root ../av_before/mvp --markets AU,DE --out before.jsonl
  python scripts/regression_diff.py dump --root . --markets AU,DE --out after.jsonl
  # 3. 对比：按市场汇总结论分布的变化，再列出每条变了的样本
  python scripts/regression_diff.py diff before.jsonl after.jsonl

导出的文件里有原始输入，只放在本机，不要提交。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def dump(root: str, markets: list[str], parser: str, n_real: int, n_synth: int, out: str) -> None:
    root = str(Path(root).resolve())
    sys.path[:0] = [root + "/scripts", root]  # 用 --root 那份代码（旧版本或当前版本）
    from evaluate_markets import judge_real, judge_synth, real_cases, synthetic_cases
    from avmvp.intl.engine import Engine
    from avmvp.intl.reference import MarketReference
    with open(out, "w", encoding="utf-8") as f:
        for mk in markets:
            ref = MarketReference.load(mk)
            eng = Engine(mk, parser, ref)
            for kind, cases, judge in (("real", real_cases(mk, n_real, "dev"), judge_real),
                                       ("synth", synthetic_cases(ref, n_synth, "dev"), judge_synth)):
                for c in cases:
                    r = eng.validate(c["input"])
                    f.write(json.dumps({"market": mk, "kind": kind, "input": c["input"], "outcome": judge(eng, r, c),
                                        "action": r.action, "granularity": r.granularity, "reasons": r.reasons[:6]},
                                       ensure_ascii=False) + "\n")
            print(f"{mk} 完成", flush=True)


def diff(before: str, after: str, show: int) -> None:
    a = [json.loads(x) for x in open(before, encoding="utf-8")]
    b = [json.loads(x) for x in open(after, encoding="utf-8")]
    if len(a) != len(b) or any(x["input"] != y["input"] for x, y in zip(a, b)):
        sys.exit("两份导出的样本不一致：要用同样的 --markets 和条数导出")
    groups = sorted({(x["market"], x["kind"]) for x in a})
    for mk, kind in groups:
        ca = Counter(x["outcome"] for x in a if (x["market"], x["kind"]) == (mk, kind))
        cb = Counter(y["outcome"] for y in b if (y["market"], y["kind"]) == (mk, kind))
        moved = {k: (ca[k], cb[k]) for k in sorted(set(ca) | set(cb)) if ca[k] != cb[k]}
        n = sum(ca.values())
        print(f"{mk} {kind:5} {n} 条：" + ("没有变化" if not moved else
                                           "，".join(f"{k} {u} → {v}" for k, (u, v) in moved.items())))
    changed = [(x, y) for x, y in zip(a, b) if x["outcome"] != y["outcome"]]
    print(f"\n结论变了的样本 {len(changed)} 条" + (f"（只列前 {show} 条）" if len(changed) > show else "") + "：")
    for x, y in changed[:show]:
        print(f"[{x['market']} {x['kind']}] {x['outcome']} → {y['outcome']} | {x['input'][:90]}\n"
              f"    之前 {x['action']} / {x['granularity']} / {','.join(x['reasons'])}\n"
              f"    之后 {y['action']} / {y['granularity']} / {','.join(y['reasons'])}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump", help="用 --root 那份代码跑开发集，逐条导出结论")
    d.add_argument("--root", default=".", help="mvp 目录（旧版本的 worktree 或当前目录）")
    d.add_argument("--markets", required=True)
    d.add_argument("--parser", default="hybrid")
    d.add_argument("--n-real", type=int, default=600)
    d.add_argument("--n-synth", type=int, default=1000)
    d.add_argument("--out", required=True)
    c = sub.add_parser("diff", help="对比两份导出")
    c.add_argument("before")
    c.add_argument("after")
    c.add_argument("--show", type=int, default=200)
    args = ap.parse_args()
    if args.cmd == "dump":
        dump(args.root, [m.strip().upper() for m in args.markets.split(",") if m.strip()], args.parser,
             args.n_real, args.n_synth, args.out)
    else:
        diff(args.before, args.after, args.show)


if __name__ == "__main__":
    main()
