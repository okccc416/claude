"""贝叶斯打分评测：开发集训练，测试集上与规则方案对比。

对比四种做法：
  规则（当前）                 手工证据优先级选候选，无置信度
  贝叶斯选择 · 朴素            逐字段证据权重相加（假设字段独立），按后验概率选候选
  贝叶斯选择 · 联合证据        "邮编 × 楼栋号 × 道路"组合整体统计权重，按后验概率选候选
  规则选择 + 贝叶斯置信度      规则选候选；置信度 = 同类结论在开发集里的实际正确率（Beta 平滑）

  python scripts/evaluate_bayes.py
输出：models/bayes_sg.json、models/confidence_sg.json、reports/bayes_eval_report.md
"""

from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from avmvp import ReferenceDB, Validator  # noqa: E402
from avmvp.bayes import THRESHOLDS, BayesModel, BayesValidator, ConfidenceModel, ConfidenceValidator  # noqa: E402
from avmvp.validator import ACCEPT, ADD_SUB, CONFIRM  # noqa: E402
from evaluate import load_golden  # noqa: E402
from evaluate import metrics as golden_metrics  # noqa: E402
from evaluate_noisy import load as load_noisy  # noqa: E402
from evaluate_noisy import summarize as noisy_metrics  # noqa: E402

BINS = [0.0, 0.5, 0.7, 0.9, 0.95, 0.99, 0.999, 1.0000001]


def pct(x):
    return f"{100 * x:.1f}%"


def run(v, rows):
    preds, lat, confs = [], [], []
    for r in rows:
        t = time.perf_counter()
        res = v.validate(r["input"])
        lat.append((time.perf_counter() - t) * 1000)
        a = ACCEPT if res.action == ADD_SUB else res.action
        preds.append((a, res.entity.eid if res.entity else None))
        confs.append(res.confidence)
    return preds, lat, confs


def calibration(rows, preds, confs):
    """置信度 vs 实际正确率。正确 = 给出的地址正确，或判"没有可用地址"且确实没有。"""
    pts = [(c, p[1] == r["expected_eid"], p[1] is not None) for r, p, c in zip(rows, preds, confs)]
    table, ece = [], 0.0
    for lo, hi in zip(BINS, BINS[1:]):
        sel = [(c, ok) for c, ok, _ in pts if lo <= c < hi]
        if sel:
            conf, acc = sum(c for c, _ in sel) / len(sel), sum(ok for _, ok in sel) / len(sel)
            ece += len(sel) / len(pts) * abs(conf - acc)
            table.append((lo, min(hi, 1.0), len(sel), conf, acc))
    n_has = sum(1 for r in rows if r["expected_eid"] is not None)
    selective = []
    for t in (0.9, 0.95, 0.99, 0.995, 0.999):
        sel = [ok for c, ok, is_addr in pts if is_addr and c >= t]
        selective.append((t, len(sel) / max(n_has, 1), (len(sel) - sum(sel)) / max(len(sel), 1), len(sel)))
    brier = sum((c - ok) ** 2 for c, ok, _ in pts) / len(pts)
    return {"table": table, "ece": ece, "brier": brier, "selective": selective}


def main() -> None:
    t0 = time.time()
    db = ReferenceDB.load(ROOT / "data" / "reference_sg.csv.gz")
    v = Validator(db)

    dev = load_golden("dev") + load_noisy("dev")
    random.Random(11).shuffle(dev)
    cut = int(len(dev) * 0.7)
    naive = BayesModel.fit(v, dev[:cut], dev[cut:], mode="independent")
    joint = BayesModel.fit(v, dev[:cut], dev[cut:], mode="joint")
    joint.save(ROOT / "models" / "bayes_sg.json")
    cm = ConfidenceModel().fit((res, (res.entity.eid if res.entity else None) == r["expected_eid"])
                               for r in dev for res in [v.validate(r["input"])])
    cm.save(ROOT / "models" / "confidence_sg.json")
    systems = {
        "规则（当前）": v,
        "贝叶斯选择 · 朴素": BayesValidator(v, naive),
        "贝叶斯选择 · 联合证据": BayesValidator(v, joint),
        "规则选择 + 贝叶斯置信度": ConfidenceValidator(v, cm),
    }
    print(f"训练完成：开发集 {len(dev)} 条；联合证据组合 {len(joint.joint)} 种；置信度类别 {len(cm.table)} 个")

    L = ["# 贝叶斯打分评测报告（自动生成）\n",
         f"- 训练数据：开发集 {len(dev):,} 条（标准集开发集 + 噪声集开发集）；测试集不参与训练",
         f"- 贝叶斯选择：{cut:,} 条统计证据权重，{len(dev) - cut:,} 条拟合校准温度"
         f"（朴素 T={naive.temperature}，联合 T={joint.temperature}）",
         "- 规则 + 置信度：置信度 = 同类结论在开发集里的实际正确率，Beta 先验平滑，稀有类别逐级退回更粗的类别",
         f"- 默认档位 BALANCED：置信度 ≥ {THRESHOLDS['BALANCED'][0]} 才可直接通过\n"]
    out = {}
    sets = {"标准集（4,000 条）": ("golden", load_golden("test")), "噪声集（1,800 条）": ("noisy", load_noisy("test"))}
    for name, (kind, rows) in sets.items():
        runs = {label: run(sysm, rows) for label, sysm in systems.items()}
        rp = runs["规则（当前）"][0]
        if kind == "golden":
            head, cols = ("完全正确率", "full_correct"), [("误收率", "FAR"), ("误拒率", "FRR"), ("静默错误率", "silent_wrong")]
            mets = {k: golden_metrics(rows, p, lat) for k, (p, lat, _) in runs.items()}
        else:
            head, cols = ("地址识别率", "addr_found"), [("直接通过率", "clean_accept"), ("误拒率", "false_reject"),
                                                      ("静默错误率", "silent_wrong")]
            mets = {k: noisy_metrics(k, rows, p, lat) for k, (p, lat, _) in runs.items()}
        L += [f"## {name}\n", "### 准确率\n",
              f"| 做法 | {head[0]} | " + " | ".join(c for c, _ in cols) + " | 相对规则：改对 / 改错 | 延迟 P50 / P95 |",
              "|---|---|" + "---|" * len(cols) + "---|---|"]
        for label, m in mets.items():
            p = runs[label][0]
            fixed = sum(1 for r, x, y in zip(rows, rp, p) if x[1] != r["expected_eid"] and y[1] == r["expected_eid"])
            broke = sum(1 for r, x, y in zip(rows, rp, p) if x[1] == r["expected_eid"] and y[1] != r["expected_eid"])
            lat = m["latency_ms"]
            L.append(f"| {label} | **{pct(m[head[1]])}** | " + " | ".join(pct(m[k]) for _, k in cols)
                     + f" | {fixed} / {broke} | {lat['p50']:.1f} / {lat['p95']:.1f} ms |")
        preds, _, confs = runs["规则选择 + 贝叶斯置信度"]
        cal = calibration(rows, preds, confs)
        jp, _, jc = runs["贝叶斯选择 · 联合证据"]
        cal_joint = calibration(rows, jp, jc)
        out[name] = {k: {kk: vv for kk, vv in m.items() if kk != "errors"} for k, m in mets.items()}
        out[name]["calibration"] = cal
        L += ["\n### 置信度准不准（规则选择 + 贝叶斯置信度）\n",
              "| 置信度区间 | 样本数 | 平均置信度 | 实际正确率 |", "|---|---|---|---|"]
        for lo, hi, n, conf, acc in cal["table"]:
            L.append(f"| {lo:.3f} – {hi:.3f} | {n} | {100 * conf:.2f}% | {100 * acc:.2f}% |")
        L.append(f"\n期望校准误差 ECE = **{cal['ece']:.4f}**（越接近 0 越准；贝叶斯选择 · 联合证据为 {cal_joint['ece']:.4f}），"
                 f"Brier = {cal['brier']:.4f}\n")
        L += ["### 按置信度门槛自动通过：能通过多少、错多少\n",
              "| 门槛（置信度 ≥） | 自动通过的比例（占有地址的输入） | 自动通过中的错误率 | 条数 |", "|---|---|---|---|"]
        for t, cov, err, n in cal["selective"]:
            L.append(f"| {t} | {pct(cov)} | {100 * err:.2f}% | {n} |")
        L.append("")

    top = sorted(cm.table.items(), key=lambda kv: -kv[1][1])
    L += ["## 置信度从哪来：开发集中最常见的结论类别\n", "| 结论类别 | 开发集条数 | 其中正确 | 置信度 |", "|---|---|---|---|"]
    for sig, (c, n) in [kv for kv in top if kv[0].count("|") >= 3 or kv[0].startswith("FIX:")][:14]:
        L.append(f"| `{sig}` | {n} | {c} | {100 * cm_conf(cm, sig):.2f}% |")
    L += ["\n## 联合证据权重（log2 似然比，开发集统计；正数支持\"就是这个地址\"）\n",
          "| 邮编 \\| 楼栋号 \\| 道路 | 权重 |", "|---|---|"]
    for pt, w in sorted(joint.joint.items(), key=lambda kv: -kv[1])[:8] + sorted(joint.joint.items(), key=lambda kv: kv[1])[:5]:
        L.append(f"| {pt.replace('|', ' / ')} | {w:+.1f} |")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "bayes_eval_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str),
                                                               encoding="utf-8")
    (ROOT / "reports" / "bayes_eval_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"\n完成，用时 {time.time() - t0:.0f}s")


def cm_conf(cm: ConfidenceModel, sig: str) -> float:
    """按签名直接查置信度（用于报告展示）。"""
    parts = sig.split(":", 1)
    if parts[0] == "FIX":
        chain = [sig, "FIX:" + parts[1].split("+")[0], "FIX"]
    else:
        core = "|".join(parts[1].split("|")[:3])
        chain = [sig, f"ENTITY:{core}", "ENTITY"]
    est = 0.5
    for s in reversed(chain):
        c, n = cm.table.get(s, (0, 0))
        est = (c + 1) / (n + 2) if s in ("ENTITY", "FIX") else (c + cm.strength * est) / (n + cm.strength)
    return est


if __name__ == "__main__":
    main()
