"""本地小模型评测：同一份评测集上对比三种方案。

  规则               当前 MVP（不调用模型）
  规则 + 模型兜底     规则处理不好时才调用本地模型拆字段，再回到参考库裁决（avmvp/llm_fallback.py）
  纯模型（--pure）    只用模型：模型说"地址完整"就算通过，不查参考库真假；用于量化模型编造地址的风险

用法（先在本机启动模型服务，例如 `ollama pull qwen2.5:1.5b && ollama serve`）：
  python scripts/evaluate_llm.py --model qwen2.5:1.5b                        # 噪声测试集
  python scripts/evaluate_llm.py --set golden_test --model qwen2.5:3b --pure
  python scripts/evaluate_llm.py --api openai --endpoint http://127.0.0.1:8080 --model qwen   # llama.cpp / vLLM
  python scripts/evaluate_llm.py --limit 300                                  # 先抽样跑一小批看看
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp import ReferenceDB, Validator  # noqa: E402
from avmvp.llm_fallback import LLMAssistedValidator, LocalLLM  # noqa: E402
from avmvp.normalize import match_key  # noqa: E402
from avmvp.validator import ACCEPT, ADD_SUB, CONFIRM, FIX  # noqa: E402


def load(name: str) -> list[dict]:
    with open(ROOT / "data" / f"{name}.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["expected_eid"] = int(r["expected_eid"]) if r["expected_eid"] else None
    return rows


def metrics(rows, preds, lat) -> dict:
    has = [i for i, r in enumerate(rows) if r["expected_eid"] is not None]
    none = [i for i, r in enumerate(rows) if r["expected_eid"] is None]

    def ok(i):
        return preds[i][0] != FIX and preds[i][1] == rows[i]["expected_eid"]

    s = sorted(lat)
    return {
        "addr_found": sum(ok(i) for i in has) / max(len(has), 1),
        "direct_pass": sum(ok(i) and preds[i][0] == ACCEPT for i in has) / max(len(has), 1),
        "false_reject": sum(preds[i][0] == FIX for i in has) / max(len(has), 1),
        "silent_wrong": sum(preds[i][0] == ACCEPT and (rows[i]["expected_eid"] is None or preds[i][1] != rows[i]["expected_eid"])
                            for i in range(len(rows))) / len(rows),
        "bad_rejected": sum(preds[i][0] == FIX for i in none) / max(len(none), 1),
        "p50_ms": s[len(s) // 2], "p95_ms": s[int(len(s) * 0.95)],
    }


def run(v, rows):
    preds, lat = [], []
    for r in rows:
        t = time.perf_counter()
        res = v.validate(r["input"])
        lat.append((time.perf_counter() - t) * 1000)
        a = ACCEPT if res.action == ADD_SUB else res.action
        preds.append((a, res.entity.eid if res.entity else None))
    return preds, lat


def pure_llm(llm, db, rows):
    """纯模型：模型说地址完整就算通过；只为打分才去参考库找它说的是哪一栋楼（找不到即判错）。"""
    preds, lat = [], []
    for r in rows:
        t = time.perf_counter()
        try:
            f = llm.extract(r["input"])
        except Exception:
            f = {"is_complete_address": False}
        lat.append((time.perf_counter() - t) * 1000)
        eid = None
        blk = (f.get("block") or "").upper().replace("BLK", "").strip()
        ids = db.by_postal.get("".join(ch for ch in f.get("postal_code", "") if ch.isdigit()), [])
        hit = [i for i in ids if db.entities[i].blk == blk] or (ids if len(ids) == 1 else [])
        if not hit and blk and f.get("street"):
            hit = db.by_blk_road.get((blk, match_key(f["street"])), [])
        eid = hit[0] if len(hit) == 1 else None
        preds.append((ACCEPT, eid) if f.get("is_complete_address") else (FIX, None))
    return preds, lat


def pct(x):
    return f"{100 * x:.1f}%"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="noisy_test", help="data/<set>.csv，如 noisy_test / golden_test")
    ap.add_argument("--endpoint", default="http://127.0.0.1:11434")
    ap.add_argument("--model", default="qwen2.5:1.5b")
    ap.add_argument("--api", default="ollama", choices=["ollama", "openai"])
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--limit", type=int, default=0, help="随机抽样条数（0 = 全量）")
    ap.add_argument("--pure", action="store_true", help="同时评测纯模型方案（每条都调用模型，较慢）")
    args = ap.parse_args()

    rows = load(args.set)
    if args.limit:
        rows = random.Random(7).sample(rows, min(args.limit, len(rows)))
    db = ReferenceDB.load(ROOT / "data" / "reference_sg.csv.gz")
    rules = Validator(db)
    llm = LocalLLM(endpoint=args.endpoint, model=args.model, api=args.api, timeout=args.timeout)

    results = {}
    results["规则（当前 MVP）"] = metrics(rows, *run(rules, rows))
    hybrid = LLMAssistedValidator(rules, llm)
    results[f"规则 + 模型兜底（{args.model}）"] = metrics(rows, *run(hybrid, rows))
    st = hybrid.stats
    if args.pure:
        results[f"纯模型（{args.model}）"] = metrics(rows, *pure_llm(llm, db, rows))

    s = sorted(st.latency_ms) or [0.0]
    fb = {"calls": st.calls, "call_rate": st.calls / len(rows), "errors": st.errors, "used": st.used,
          "llm_p50_ms": s[len(s) // 2], "llm_p95_ms": s[int(len(s) * 0.95)]}
    out = {"set": args.set, "n": len(rows), "model": args.model, "api": args.api, "results": results, "fallback": fb}
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / f"llm_eval_{args.set}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                                                 encoding="utf-8")
    L = [f"# 本地小模型评测：{args.model}（{args.api}）\n",
         f"- 评测集：`data/{args.set}.csv`，{len(rows):,} 条" + ("（随机抽样）" if args.limit else ""),
         f"- 兜底调用 {st.calls} 次（{pct(fb['call_rate'])}），出错 / 超时 {st.errors} 次，采纳模型结果 {st.used} 次",
         f"- 模型单次调用延迟 P50 {fb['llm_p50_ms']:.0f} ms / P95 {fb['llm_p95_ms']:.0f} ms\n",
         "| 方案 | 地址识别率 ↑ | 直接通过率 ↑ | 误拒率 ↓ | 静默错误率 ↓ | 坏输入拒绝率 ↑ | 单条延迟 P50 / P95 |",
         "|---|---|---|---|---|---|---|"]
    for name, m in results.items():
        L.append(f"| {name} | **{pct(m['addr_found'])}** | {pct(m['direct_pass'])} | {pct(m['false_reject'])} | "
                 f"{pct(m['silent_wrong'])} | {pct(m['bad_rejected'])} | {m['p50_ms']:.1f} / {m['p95_ms']:.1f} ms |")
    (ROOT / "reports" / f"llm_eval_{args.set}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
