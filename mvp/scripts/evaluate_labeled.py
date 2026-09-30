"""用模拟订单标注数据（labeled/orders_sg_v1.csv）评测校验器，并用其中的训练部分重新统计置信度。

回答三个问题：
1. 在接近真实分布的订单上，规则校验器的自动通过率、静默错误率、误拒率是多少？错在哪些场景？
2. 置信度模型用"订单数据"重新统计后，能不能区分出有风险的结论（与只用合成测试集统计的旧模型对比）？
3. 按置信度设门槛，自动通过比例与错误率怎么取舍？

  python scripts/evaluate_labeled.py
输出：reports/labeled_eval_report.md、reports/labeled_eval_results.json、models/confidence_sg_orders.json
训练部分只用于统计置信度；所有指标都在测试部分上计算（按真实地址切分，与训练部分不重叠）。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp import ReferenceDB, Validator  # noqa: E402
from avmvp.bayes import THRESHOLDS, ConfidenceModel  # noqa: E402
from avmvp.validator import ACCEPT, ADD_SUB, CONFIRM, FIX  # noqa: E402

OUTCOMES = ["正确", "正确拒绝", "多余确认", "漏报", "误拒", "错误建议", "静默错误"]
OUTCOME_HELP = {
    "正确": "地址对，结论符合标注规范",
    "正确拒绝": "判 FIX，且仅凭文字确实无法确定真实地址",
    "多余确认": "地址对，本可直接通过却要求用户确认（多一次打扰，不造成错误）",
    "漏报": "地址对，但该提示的没提示（如缺单元号、需纠错的改动）就直接通过",
    "误拒": "文字足以确定地址，却判 FIX",
    "错误建议": "给出的地址不对，但要求用户确认（用户有机会发现）",
    "静默错误": "给出的地址不对，却直接通过（ACCEPT / 仅提示补单元号）",
}
BINS = [0.0, 0.5, 0.7, 0.9, 0.95, 0.99, 0.999, 1.0000001]
STATUS_CN = {"confirmed": "确认", "corrected": "纠错", "inferred": "补全", "replaced": "替换", "plausible": "未证实",
             "missing": "缺失", "None": "—"}


def same_address(res, r: dict) -> bool:
    """给出的地址是否就是真实地址（参考库里同一地址可能有两条记录，按楼栋 + 道路 + 邮编比较）。"""
    if res.entity is None or r["truth_eid"] is None:
        return False
    e = res.entity
    return (e.blk, e.road_key, e.postal) == r["truth_key"]


def load(path: str | Path, db: ReferenceDB | None = None) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["truth_eid"] = int(r["truth_eid"]) if r["truth_eid"] else None
        r["acceptable"] = set(r["acceptable_actions"].split("|"))
        r["tags"] = [t for t in r["error_tags"].split("|") if t]
        t = db.entities[r["truth_eid"]] if db is not None and r["truth_eid"] is not None else None
        r["truth_key"] = (t.blk, t.road_key, t.postal) if t else None
    return rows


def correct(r: dict, res) -> bool:
    """置信度的口径：给出地址时 = 就是真实地址；判 FIX 时 = 仅凭文字确实无法确定真实地址。"""
    if res.entity is not None:
        return same_address(res, r)
    return r["text_resolution"] != "RESOLVABLE"


def outcome(r: dict, res) -> str:
    if res.entity is None:
        return "误拒" if r["text_resolution"] == "RESOLVABLE" else "正确拒绝"
    if not same_address(res, r):
        return "静默错误" if res.action in (ACCEPT, ADD_SUB) else "错误建议"
    if res.action in r["acceptable"]:
        return "正确"
    if res.action == ACCEPT:
        return "漏报"
    if r["gold_action"] == ACCEPT:
        return "多余确认"
    return "正确"


def unit_key(u: str | None) -> tuple[str, str] | None:
    if not u or not u.startswith("#") or "-" not in u:
        return None
    f, n = u[1:].split("-", 1)
    return (f if f.startswith("B") else str(int(f)), n.lstrip("0") or "0")


def pct(x: float, digits: int = 1) -> str:
    return f"{100 * x:.{digits}f}%"


def summarize(rows: list[dict], results: list) -> dict:
    n = len(rows)
    oc = Counter(outcome(r, res) for r, res in zip(rows, results))
    acts = Counter(res.action for res in results)
    passed = [(r, res) for r, res in zip(rows, results) if res.action in (ACCEPT, ADD_SUB)]
    resolvable = [(r, res) for r, res in zip(rows, results) if r["text_resolution"] == "RESOLVABLE"]
    unit_missing = [(r, res) for r, res in resolvable if "UNIT_MISSING" in r["tags"] and r["unit_required"] == "Y"
                    and same_address(res, r)]
    unit_given = [(r, res) for r, res in zip(rows, results) if r["truth_unit"] and "unit=ok" in r["field_states"]
                  and same_address(res, r)]
    judged = [(r, res) for r, res in zip(rows, results) if r["text_resolution"] != "MISLEADING"]
    return {
        "n": n,
        "outcomes": {k: oc[k] / n for k in OUTCOMES},
        "auto_pass": acts[ACCEPT] / n,
        "direct_pass": (acts[ACCEPT] + acts[ADD_SUB]) / n,
        "error_in_pass": sum(outcome(r, res) == "静默错误" for r, res in passed) / max(len(passed), 1),
        "silent_error": oc["静默错误"] / n,
        "resolvable_found": sum(same_address(res, r) for r, res in resolvable) / max(len(resolvable), 1),
        "false_reject": sum(res.action == FIX for _, res in resolvable) / max(len(resolvable), 1),
        "decision_ok": sum(outcome(r, res) in ("正确", "正确拒绝") for r, res in judged) / max(len(judged), 1),
        "unit_missing_flagged": sum(res.action in (ADD_SUB, CONFIRM) for _, res in unit_missing)
                                / max(len(unit_missing), 1),
        "unit_missing_n": len(unit_missing),
        "unit_correct": sum(unit_key(res.parsed.unit) == unit_key(r["truth_unit"]) for r, res in unit_given)
                        / max(len(unit_given), 1),
    }


def calibration(pairs: list[tuple[float, bool, bool]]) -> dict:
    """pairs = [(置信度, 是否正确, 是否给出了地址)]。"""
    table, ece = [], 0.0
    for lo, hi in zip(BINS, BINS[1:]):
        sel = [(c, ok) for c, ok, _ in pairs if lo <= c < hi]
        if sel:
            conf, acc = sum(c for c, _ in sel) / len(sel), sum(ok for _, ok in sel) / len(sel)
            ece += len(sel) / len(pairs) * abs(conf - acc)
            table.append((lo, min(hi, 1.0), len(sel), conf, acc))
    brier = sum((c - ok) ** 2 for c, ok, _ in pairs) / len(pairs)
    return {"table": table, "ece": ece, "brier": brier, "auroc": auroc([(c, ok) for c, ok, has in pairs if has])}


def auroc(scored: list[tuple[float, bool]]) -> float | None:
    """给出地址的结论里：随机取一对（一对一错），对的那条置信度更高的概率。0.5 = 没有区分度。"""
    pos = [c for c, ok in scored if ok]
    neg = [c for c, ok in scored if not ok]
    if not pos or not neg:
        return None
    ranked = sorted([(c, 1) for c in pos] + [(c, 0) for c in neg])
    rank_sum, i = 0.0, 0
    while i < len(ranked):
        j = i
        while j < len(ranked) and ranked[j][0] == ranked[i][0]:
            j += 1
        avg = (i + j + 1) / 2  # 并列取平均名次
        rank_sum += avg * sum(lbl for _, lbl in ranked[i:j])
        i = j
    return (rank_sum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def gate(rows, results, confs, threshold: float) -> dict:
    """按置信度门槛把 ACCEPT 降为 CONFIRM 之后的通过率与错误。"""
    passed = [(r, res) for r, res, c in zip(rows, results, confs)
              if res.action in (ACCEPT, ADD_SUB) and (res.action == ADD_SUB or c >= threshold)]
    auto = [(r, res) for r, res, c in zip(rows, results, confs) if res.action == ACCEPT and c >= threshold]
    wrong = sum(not same_address(res, r) for r, res in passed)
    return {"threshold": threshold, "auto_pass": len(auto) / len(rows), "silent_error": wrong / len(rows),
            "error_in_pass": wrong / max(len(passed), 1), "n_pass": len(passed)}


def describe(sig: str) -> str:
    """把置信度类别签名翻成中文。"""
    if sig.startswith("FIX"):
        return "判 FIX：" + (sig.split(":", 1)[1] or "无原因码") if ":" in sig else "判 FIX"
    parts = sig.split(":", 1)[1].split("|")
    premise, route, postal = (STATUS_CN.get(x, x) for x in parts[:3])
    out = f"楼栋{premise} · 道路{route} · 邮编{postal}"
    flags = dict(p.split("=") for p in parts[3:] if "=" in p)
    if flags.get("bld") == "y":
        out += " · 楼宇名吻合"
    if flags.get("unres") == "y":
        out += " · 有未识别文字"
    if flags.get("poi") == "y":
        out += " · 仅楼宇名"
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", default=str(ROOT / "labeled" / "orders_sg_v1.csv"))
    ap.add_argument("--reference", default=str(ROOT / "data" / "reference_sg.csv.gz"))
    ap.add_argument("--old-model", default=str(ROOT / "models" / "confidence_sg.json"))
    args = ap.parse_args()
    t0 = time.time()
    db = ReferenceDB.load(args.reference)
    v = Validator(db)
    rows = load(args.orders, db)
    results = []
    lat = []
    for r in rows:
        t = time.perf_counter()
        results.append(v.validate(r["input"]))
        lat.append((time.perf_counter() - t) * 1000)
    train = [(r, res) for r, res in zip(rows, results) if r["split"] == "train"]
    test = [(r, res) for r, res in zip(rows, results) if r["split"] == "test"]
    t_rows, t_res = [r for r, _ in test], [res for _, res in test]
    print(f"校验完成：{len(rows)} 单（训练 {len(train)} / 测试 {len(test)}），{time.time() - t0:.0f}s")

    new = ConfidenceModel().fit((res, correct(r, res)) for r, res in train)
    new.save(ROOT / "models" / "confidence_sg_orders.json")
    old = ConfidenceModel.load(args.old_model)
    overall = summarize(t_rows, t_res)

    def segment(key_fn, min_n=15):
        groups = defaultdict(list)
        for r, res in test:
            for k in key_fn(r):
                groups[k].append((r, res))
        return {k: summarize([r for r, _ in g], [res for _, res in g]) for k, g in groups.items() if len(g) >= min_n}

    by_res = segment(lambda r: [r["text_resolution"]], 1)
    by_channel = segment(lambda r: [r["channel"]])
    by_ptype = segment(lambda r: [r["property_type"] or "（非地址）"])
    by_tag = segment(lambda r: r["tags"] or ["（无错误）"])

    conf = {}
    for name, model in (("旧模型（合成测试集统计）", old), ("新模型（订单训练部分统计）", new)):
        cs = [model.confidence(res) for res in t_res]
        pairs = [(c, correct(r, res), res.entity is not None) for r, res, c in zip(t_rows, t_res, cs)]
        conf[name] = {"calibration": calibration(pairs),
                      "gates": [gate(t_rows, t_res, cs, th) for th in (0.0, 0.9, 0.95, 0.97, 0.99, 0.995)],
                      "profiles": {p: gate(t_rows, t_res, cs, THRESHOLDS[p][0]) for p in THRESHOLDS}}

    fine = [(sig, c, n) for sig, (c, n) in new.table.items() if n >= 20 and (sig.count("|") >= 3 or sig.startswith("FIX:"))]
    risky = sorted(fine, key=lambda x: x[1] / x[2])[:12]
    common = sorted(fine, key=lambda x: -x[2])[:10]

    # 静默错误 / 误拒样例（按主要错误标签分组）
    examples = defaultdict(list)
    for r, res in test:
        o = outcome(r, res)
        if o in ("静默错误", "误拒", "错误建议", "漏报"):
            key = (o, r["text_resolution"], "+".join(t for t in r["tags"] if not t.startswith(("NOISE", "ABBREV",
                                                                                                "UNIT_FORMAT")))
                   or "（无）")
            got = f"{res.entity.blk} {res.entity.road} {res.entity.postal}" if res.entity else "—"
            examples[key].append((r["order_id"], r["input"].replace("\n", " / "), res.action, got,
                                  f"{r['truth_blk']} {r['truth_street']} {r['truth_postal']}".strip()))

    out = {"overall": overall, "by_resolution": by_res, "by_channel": by_channel, "by_property_type": by_ptype,
           "by_tag": by_tag, "confidence": conf,
           "risky_classes": [(s, c, n) for s, c, n in risky], "sizes": {"train": len(train), "test": len(test)},
           "latency_ms": {"p50": sorted(lat)[len(lat) // 2], "p95": sorted(lat)[int(len(lat) * 0.95)]}}
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "labeled_eval_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    # ------------------------------------------------------------------ 报告
    L = ["# 模拟订单标注数据评测报告（自动生成）\n",
         f"- 数据：`labeled/orders_sg_v1.csv`，共 {len(rows):,} 单；训练 {len(train):,} 单只用于统计置信度，"
         f"以下指标均在测试 {len(test):,} 单上计算（按真实地址切分，互不重叠）",
         "- 校验器：规则方案，默认 BALANCED 档，未加载楼栋属性表",
         f"- 单条延迟 P50 {out['latency_ms']['p50']:.1f} ms / P95 {out['latency_ms']['p95']:.1f} ms\n",
         "## 1. 总体\n", "| 指标 | 数值 | 说明 |", "|---|---|---|",
         f"| 自动通过率 | {pct(overall['auto_pass'])} | 结论为 ACCEPT 的订单占比 |",
         f"| 直接通过率 | {pct(overall['direct_pass'])} | ACCEPT + 仅提示补单元号 |",
         f"| 直接通过中的错误率 | {pct(overall['error_in_pass'], 2)} | 直接通过的订单里地址不对的比例 |",
         f"| 静默错误率 | {pct(overall['silent_error'], 2)} | 地址不对却直接通过，占全部订单 |",
         f"| 可确定地址的识别率 | {pct(overall['resolvable_found'])} | 文字足以确定地址的订单里，找对地址的比例 |",
         f"| 误拒率 | {pct(overall['false_reject'])} | 文字足以确定地址，却判 FIX |",
         f"| 结论合理率 | {pct(overall['decision_ok'])} | 结论符合标注规范（不含\"误导\"类） |",
         f"| 缺单元号检出率 | {pct(overall['unit_missing_flagged'])} | 多单元楼缺单元号时，提示补充的比例（{overall['unit_missing_n']} 单） |",
         f"| 单元号解析正确率 | {pct(overall['unit_correct'])} | 写了单元号且地址找对时，单元号解析正确的比例 |\n",
         "### 结论分布\n", "| 结果 | 占比 | 含义 |", "|---|---|---|"]
    for k in OUTCOMES:
        L.append(f"| {k} | {pct(overall['outcomes'][k])} | {OUTCOME_HELP[k]} |")

    def seg_table(title, seg, order=None):
        L.extend([f"\n### {title}\n",
                  "| 分组 | 单数 | 正确 + 正确拒绝 | 多余确认 | 漏报 | 误拒 | 错误建议 | 静默错误 |",
                  "|---|---|---|---|---|---|---|---|"])
        keys = order or sorted(seg, key=lambda k: -seg[k]["n"])
        for k in keys:
            if k not in seg:
                continue
            o = seg[k]["outcomes"]
            L.append(f"| {k} | {seg[k]['n']} | {pct(o['正确'] + o['正确拒绝'])} | {pct(o['多余确认'])} | "
                     f"{pct(o['漏报'])} | {pct(o['误拒'])} | {pct(o['错误建议'])} | {pct(o['静默错误'])} |")

    L.append("\n## 2. 分场景\n")
    seg_table("按\"仅凭文字能判断到什么程度\"", by_res,
              ["RESOLVABLE", "AMBIGUOUS", "CONFLICTING", "MISLEADING", "NOT_IN_REFERENCE", "OUT_OF_REGION",
               "NO_ADDRESS"])
    seg_table("按渠道", by_channel)
    seg_table("按物业类型", by_ptype)
    seg_table("按错误标签（一单可有多个标签，至少 15 单才列出）", by_tag)

    L += ["\n## 3. 置信度：旧模型 vs 用订单数据重新统计\n",
          "| 模型 | 校准误差 ECE | Brier | 区分度 AUROC（给出地址的结论） |", "|---|---|---|---|"]
    for name, c in conf.items():
        a = c["calibration"]["auroc"]
        L.append(f"| {name} | {c['calibration']['ece']:.4f} | {c['calibration']['brier']:.4f} | "
                 f"{'—' if a is None else f'{a:.3f}'} |")
    L.append("\nAUROC：随机取一条对的、一条错的结论，对的那条置信度更高的概率；0.5 = 完全没有区分度，1 = 完美区分。\n")
    for name, c in conf.items():
        L += [f"### {name}：置信度区间 vs 实际正确率\n", "| 置信度区间 | 单数 | 平均置信度 | 实际正确率 |",
              "|---|---|---|---|"]
        for lo, hi, n, cf, acc in c["calibration"]["table"]:
            L.append(f"| {lo:.3f} – {hi:.3f} | {n} | {pct(cf, 2)} | {pct(acc, 2)} |")
        L.append("")
    L += ["### 按置信度门槛自动通过（ACCEPT 且置信度 ≥ 门槛，否则降为 CONFIRM）\n",
          "| 模型 | 门槛 | 自动通过率 | 静默错误率 | 直接通过中的错误率 |", "|---|---|---|---|---|"]
    for name, c in conf.items():
        for g in c["gates"]:
            L.append(f"| {name} | {g['threshold']} | {pct(g['auto_pass'])} | {pct(g['silent_error'], 2)} | "
                     f"{pct(g['error_in_pass'], 2)} |")
    L += ["\n### 新模型：风险最高的结论类别（训练部分至少 20 单）\n",
          "| 结论类别 | 训练单数 | 其中正确 | 实际正确率 |", "|---|---|---|---|"]
    for sig, c, n in risky:
        L.append(f"| {describe(sig)} | {n} | {c} | {pct(c / n)} |")
    L += ["\n### 新模型：最常见的结论类别\n", "| 结论类别 | 训练单数 | 其中正确 | 实际正确率 |", "|---|---|---|---|"]
    for sig, c, n in common:
        L.append(f"| {describe(sig)} | {n} | {c} | {pct(c / n)} |")

    L.append("\n## 4. 错误样例（测试部分，每类最多 3 条）\n")
    for key, items in sorted(examples.items(), key=lambda kv: (OUTCOMES.index(kv[0][0]) * -1, -len(kv[1])))[:24]:
        o, res_label, tags = key
        L.append(f"**{o} · {res_label} · {tags}**（{len(items)} 单）\n")
        L += ["| 订单 | 输入 | 结论 | 给出的地址 | 真实地址 |", "|---|---|---|---|---|"]
        for oid, text, act, got, truth in items[:3]:
            L.append(f"| {oid} | {text.replace('|', '/')} | {act} | {got} | {truth or '—'} |")
        L.append("")
    (ROOT / "reports" / "labeled_eval_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:40]))
    print(f"\n完成，用时 {time.time() - t0:.0f}s；报告：reports/labeled_eval_report.md")


if __name__ == "__main__":
    main()
