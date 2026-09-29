"""噪声评测：同一份"真实客户输入"风格的评测集，对比改进前 / 改进后的实现以及两个对照方案。

  python scripts/evaluate_noisy.py --before-impl /path/to/old/mvp   # 旧版实现所在目录（含 avmvp 包）

指标（N1–N8 为"输入里有真实地址"，N9 为"根本没有地址"）：
  地址识别率   N1–N8 中，结论不是 FIX 且识别出的地址正确的比例（核心指标）
  直接通过率   N1–N8 中，直接 ACCEPT 且地址正确的比例（噪声被干净剥离，不需要打扰用户）
  误拒率       N1–N8 中被判 FIX 的比例
  静默错误率   全部样本中，判 ACCEPT 但地址错了或其实没有地址的比例
  无地址拒绝率 N9 中被判 FIX 的比例
  单元号保留率 带单元号的样本中，解析出的单元号与标准写法一致的比例
  电话抽取召回 注入了电话的样本中，电话号码被单独抽取出来的比例
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CAT_CN = {
    "N1_contact_info": "N1 电话 / 邮箱 / 订单号", "N2_recipient_company": "N2 收件人 / 公司名",
    "N3_delivery_notes": "N3 配送备注（中英文）", "N4_local_abbrev": "N4 本地缩写（AMK / CCK…）",
    "N5_glued_punct_case": "N5 粘连 / 标点 / 大小写", "N6_multi_typo": "N6 两处拼写错误",
    "N7_unit_variants": "N7 单元号多种写法", "N8_mixed_noise": "N8 多种噪声叠加", "N9_no_address": "N9 根本没有地址",
}


def load(name: str) -> list[dict]:
    with open(ROOT / "data" / f"noisy_{name}.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["expected_eid"] = int(r["expected_eid"]) if r["expected_eid"] else None
    return rows


def import_impl(path: str):
    """从指定目录导入 avmvp 包（用于对比旧版实现）。"""
    for mod in [m for m in sys.modules if m == "avmvp" or m.startswith("avmvp.")]:
        del sys.modules[mod]
    sys.path.insert(0, path)
    try:
        return (importlib.import_module("avmvp.reference"), importlib.import_module("avmvp.validator"),
                importlib.import_module("avmvp.baselines"))
    finally:
        sys.path.remove(path)


def run_validator(label: str, impl: str, rows: list[dict]) -> dict:
    ref_mod, val_mod, _ = import_impl(impl)
    db = ref_mod.ReferenceDB.load(ROOT / "data" / "reference_sg.csv.gz")
    v = val_mod.Validator(db)
    preds, lat, extra = [], [], []
    for r in rows:
        t = time.perf_counter()
        res = v.validate(r["input"])
        lat.append((time.perf_counter() - t) * 1000)
        action = "CONFIRM" if res.action == "CONFIRM_ADD_SUBPREMISES" else res.action
        preds.append((action, res.entity.eid if res.entity else None))
        resp = v.to_response(res)["result"]
        info = resp.get("nonAddressInfo") or {}
        extra.append({"unit": getattr(res.parsed, "unit", None), "phones": info.get("phones", []),
                      "reasons": res.reasons, "formatted": resp["address"]["formattedAddress"],
                      "unresolved": resp["address"].get("unresolvedTokens", [])})
    return summarize(label, rows, preds, lat, extra)


def summarize(label, rows, preds, lat=None, extra=None) -> dict:
    has = [i for i, r in enumerate(rows) if r["category"] != "N9_no_address"]
    junk = [i for i, r in enumerate(rows) if r["category"] == "N9_no_address"]

    def ok(i):
        return preds[i][0] != "FIX" and preds[i][1] == rows[i]["expected_eid"]

    by_cat = defaultdict(list)
    for i, r in enumerate(rows):
        by_cat[r["category"]].append(ok(i) if r["category"] != "N9_no_address" else preds[i][0] == "FIX")
    m = {
        "label": label,
        "addr_found": sum(ok(i) for i in has) / len(has),
        "clean_accept": sum(ok(i) and preds[i][0] == "ACCEPT" for i in has) / len(has),
        "false_reject": sum(preds[i][0] == "FIX" for i in has) / len(has),
        "silent_wrong": sum(preds[i][0] == "ACCEPT" and (rows[i]["expected_eid"] is None
                                                          or preds[i][1] != rows[i]["expected_eid"])
                            for i in range(len(rows))) / len(rows),
        "junk_rejected": sum(preds[i][0] == "FIX" for i in junk) / len(junk),
        "per_category": {c: sum(v) / len(v) for c, v in by_cat.items()},
    }
    if extra is not None:
        unit_rows = [i for i, r in enumerate(rows) if r["expected_unit"]]
        m["unit_kept"] = sum(extra[i]["unit"] == rows[i]["expected_unit"] for i in unit_rows) / len(unit_rows)
        phone_rows = [i for i, r in enumerate(rows) if r["expected_phones"]]
        m["phone_recall"] = sum(
            all(any(re.sub(r"\D", "", p).endswith(num) for p in extra[i]["phones"])
                for num in rows[i]["expected_phones"].split("|"))
            for i in phone_rows) / len(phone_rows)
        m["errors"] = defaultdict(list)
        for i, r in enumerate(rows):
            good = ok(i) if r["category"] != "N9_no_address" else preds[i][0] == "FIX"
            if not good and len(m["errors"][r["category"]]) < 6:
                m["errors"][r["category"]].append({
                    "input": r["input"], "expected": f"{r['expected_action']} {r['expected_address']}".strip(),
                    "got": preds[i][0], "formatted": extra[i]["formatted"], "reasons": extra[i]["reasons"]})
    if lat:
        s = sorted(lat)
        m["latency_ms"] = {"p50": s[len(s) // 2], "p95": s[int(len(s) * 0.95)]}
    return m


def run_baselines(rows, dev) -> list[dict]:
    ref_mod, _, base_mod = import_impl(str(ROOT))
    db = ref_mod.ReferenceDB.load(ROOT / "data" / "reference_sg.csv.gz")
    out = []
    fb = base_mod.FuzzyBaseline(db)
    dev_m = fb.best_matches([r["input"] for r in dev])
    fb.tune(dev_m, [(r["expected_action"], r["expected_eid"]) for r in dev])
    preds = [fb.decide(e, s) for e, s in fb.best_matches([r["input"] for r in rows])]
    out.append(summarize(fb.name, rows, preds))
    pb = base_mod.PostalBaseline(db)
    out.append(summarize(pb.name, rows, [pb.validate(r["input"]) for r in rows]))
    return out


def pct(x):
    return f"{100 * x:.1f}%" if isinstance(x, float) else "—"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="test", help="noisy_<set>.csv")
    ap.add_argument("--before-impl", help="旧版实现目录（含 avmvp 包），用于对比改进前")
    ap.add_argument("--no-baselines", action="store_true")
    args = ap.parse_args()
    rows = load(args.set)
    results = []
    if args.before_impl:
        results.append(run_validator("改进前（上一版 MVP）", args.before_impl, rows))
    results.append(run_validator("改进后（当前版本）", str(ROOT), rows))
    if not args.no_baselines:
        results += run_baselines(rows, load("dev"))
    for m in results:
        print(f"{m['label']}: 地址识别率 {pct(m['addr_found'])}，直接通过率 {pct(m['clean_accept'])}，"
              f"静默错误率 {pct(m['silent_wrong'])}，无地址拒绝率 {pct(m['junk_rejected'])}")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / f"noisy_eval_results_{args.set}.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=dict), encoding="utf-8")
    write_report(results, rows, args.set)


def write_report(results, rows, name) -> None:
    L = ["# 噪声输入评测报告（自动生成）\n",
         f"- 评测集：`data/noisy_{name}.csv`，{len(rows):,} 条（9 类），由 `scripts/make_noisy_set.py` 生成",
         "- N1–N8：输入里混有一个真实地址；N9：输入里根本没有地址\n",
         "## 1. 总览\n",
         "| 方案 | 地址识别率 ↑ | 直接通过率 ↑ | 误拒率 ↓ | 静默错误率 ↓ | 无地址拒绝率 ↑ | 单元号保留率 | 电话抽取召回 | 延迟 P50 / P95 |",
         "|---|---|---|---|---|---|---|---|---|"]
    for m in results:
        lat = m.get("latency_ms")
        ls = f"{lat['p50']:.2f} / {lat['p95']:.2f} ms" if lat else "—"
        L.append(f"| {m['label']} | **{pct(m['addr_found'])}** | {pct(m['clean_accept'])} | {pct(m['false_reject'])} | "
                 f"{pct(m['silent_wrong'])} | {pct(m['junk_rejected'])} | {pct(m.get('unit_kept'))} | "
                 f"{pct(m.get('phone_recall'))} | {ls} |")
    L += ["\n## 2. 分类别（N1–N8 为地址识别率，N9 为拒绝率）\n",
          "| 类别 | " + " | ".join(m["label"] for m in results) + " |",
          "|---|" + "---|" * len(results)]
    for c, cn in CAT_CN.items():
        L.append(f"| {cn} | " + " | ".join(pct(m["per_category"].get(c)) for m in results) + " |")
    cur = next(m for m in results if m["label"].startswith("改进后"))
    L.append("\n## 3. 改进后仍然出错的样本（每类最多 6 条）\n")
    for c, cn in CAT_CN.items():
        errs = cur["errors"].get(c)
        if not errs:
            continue
        L += [f"**{cn}**\n", "| 输入 | 期望 | 输出 | 标准化地址 | 原因码 |", "|---|---|---|---|---|"]
        for e in errs:
            L.append(f"| `{e['input']}` | {e['expected']} | {e['got']} | {e['formatted'] or '—'} | "
                     f"{', '.join(e['reasons'])} |")
        L.append("")
    (ROOT / "reports" / "noisy_eval_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
