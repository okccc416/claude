"""评测：本方案 vs 对照方案 vs 消融实验，输出 reports/eval_report.md 与 reports/eval_results.json。

指标定义见 docs/04-evaluation-framework.md 第 4 节：
  完全正确率   动作正确，且（期望非 FIX 时）给出的地址也正确
  误收率 FAR   期望 FIX 的样本中被判 ACCEPT 的比例（坏地址被放过）
  FIX 检出率   期望 FIX 的样本中被判 FIX 的比例
  误拒率 FRR   期望 ACCEPT/CONFIRM 的样本中被判 FIX 的比例（好地址被拦）
  过度打扰率   期望 ACCEPT 的样本中被判 CONFIRM 的比例
  地址正确率   期望非 FIX 且系统也未判 FIX 时，给出地址正确的比例
  静默错误率   系统判 ACCEPT 但其实是坏地址或地址给错的比例（最危险的错误，全样本口径）
"""

from __future__ import annotations

import csv
import json
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp.baselines import FuzzyBaseline, PostalBaseline  # noqa: E402
from avmvp.reference import ReferenceDB  # noqa: E402
from avmvp.validator import ACCEPT, ADD_SUB, CONFIRM, FIX, Config, Validator  # noqa: E402

CAT_ORDER = ["A_clean", "B_messy_format", "C_street_typo", "D1_missing_postcode", "D2_missing_block",
             "E_wrong_postcode", "F1_nonexistent_block", "F2_nonexistent_street", "G_building_name_only",
             "I_with_unit"]
CAT_CN = {
    "A_clean": "A 标准正确", "B_messy_format": "B 格式混乱", "C_street_typo": "C 道路拼写错误",
    "D1_missing_postcode": "D1 缺邮编", "D2_missing_block": "D2 缺楼栋号", "E_wrong_postcode": "E 邮编错误",
    "F1_nonexistent_block": "F1 楼栋号不存在", "F2_nonexistent_street": "F2 道路不存在",
    "G_building_name_only": "G 仅楼宇名", "I_with_unit": "I 带单元号",
}


def load_golden(name: str, tag: str = "") -> list[dict]:
    with open(ROOT / "data" / f"golden_{name}{tag}.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["expected_eid"] = int(r["expected_eid"]) if r["expected_eid"] else None
    return rows


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def metrics(rows: list[dict], preds: list[tuple[str, int | None]], lat_ms: list[float] | None = None) -> dict:
    def rate(num, den):
        return num / den if den else 0.0

    bad = [(r, p) for r, p in zip(rows, preds) if r["expected_action"] == FIX]
    good = [(r, p) for r, p in zip(rows, preds) if r["expected_action"] != FIX]
    clean = [(r, p) for r, p in zip(rows, preds) if r["expected_action"] == ACCEPT]
    resolved = [(r, p) for r, p in good if p[0] != FIX]

    def full_ok(r, p):
        return p[0] == r["expected_action"] and (r["expected_action"] == FIX or p[1] == r["expected_eid"])

    m = {
        "n": len(rows),
        "full_correct": rate(sum(full_ok(r, p) for r, p in zip(rows, preds)), len(rows)),
        "action_acc": rate(sum(p[0] == r["expected_action"] for r, p in zip(rows, preds)), len(rows)),
        "FAR": rate(sum(p[0] == ACCEPT for _, p in bad), len(bad)),
        "FIX_recall": rate(sum(p[0] == FIX for _, p in bad), len(bad)),
        "FRR": rate(sum(p[0] == FIX for _, p in good), len(good)),
        "UCR": rate(sum(p[0] == CONFIRM for _, p in clean), len(clean)),
        "addr_acc": rate(sum(p[1] == r["expected_eid"] for r, p in resolved), len(resolved)),
        "silent_wrong": rate(sum(p[0] == ACCEPT and (r["expected_action"] == FIX or p[1] != r["expected_eid"])
                                 for r, p in zip(rows, preds)), len(rows)),
        "per_category": {},
    }
    by_cat = defaultdict(list)
    for r, p in zip(rows, preds):
        by_cat[r["category"]].append(full_ok(r, p))
    m["per_category"] = {c: rate(sum(v), len(v)) for c, v in by_cat.items()}
    if lat_ms:
        s = sorted(lat_ms)
        m["latency_ms"] = {"p50": s[len(s) // 2], "p95": s[int(len(s) * 0.95)], "p99": s[int(len(s) * 0.99)],
                           "mean": statistics.mean(s)}
    return m


def run_validator(v: Validator, rows: list[dict], strictness: str | None = None):
    preds, lat, results = [], [], []
    for r in rows:
        t = time.perf_counter()
        res = v.validate(r["input"], strictness=strictness)
        lat.append((time.perf_counter() - t) * 1000)
        action = ACCEPT if res.action == ADD_SUB else res.action
        preds.append((action, res.entity.eid if res.entity else None))
        results.append(res)
    return preds, lat, results


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="", help="评测集文件名后缀（与 make_golden_set.py --tag 对应）")
    args = ap.parse_args()
    t0 = time.time()
    db = ReferenceDB.load(ROOT / "data" / "reference_sg.csv.gz")
    dev, test = load_golden("dev", args.tag), load_golden("test", args.tag)
    print(f"参考库 {len(db.entities):,} 个地址实体；dev {len(dev)} 条，test {len(test)} 条")

    systems: dict[str, dict] = {}

    # ---- 本方案与消融
    variants = {
        "本方案（Balanced）": Config(),
        "消融：去掉邮编交叉校验": Config(consistency_check=False),
        "消融：去掉道路拼写纠错": Config(fuzzy_road=False),
        "消融：去掉楼宇名召回": Config(building_route=False),
    }
    ours_results = None
    for name, cfg in variants.items():
        v = Validator(db, cfg)
        preds, lat, results = run_validator(v, test)
        systems[name] = metrics(test, preds, lat)
        if ours_results is None:
            ours_results, ours_preds = results, preds
        print(f"{name}: 完全正确率 {pct(systems[name]['full_correct'])}")

    # ---- 对照 B1：阈值在 dev 上调到对它最有利
    fb = FuzzyBaseline(db)
    dev_matches = fb.best_matches([r["input"] for r in dev])
    fb.tune(dev_matches, [(r["expected_action"], r["expected_eid"]) for r in dev])
    t = time.perf_counter()
    test_matches = fb.best_matches([r["input"] for r in test])
    fb_ms = (time.perf_counter() - t) * 1000 / len(test)
    preds = [fb.decide(e, s) for e, s in test_matches]
    systems[fb.name] = metrics(test, preds)
    systems[fb.name]["latency_ms"] = {"mean_batched_4cores": fb_ms}
    systems[fb.name]["thresholds"] = {"accept": fb.t_accept, "confirm": fb.t_confirm}
    print(f"{fb.name}: 阈值 accept≥{fb.t_accept} confirm≥{fb.t_confirm}，完全正确率 {pct(systems[fb.name]['full_correct'])}")

    # ---- 对照 B2
    pb = PostalBaseline(db)
    preds, lat = [], []
    for r in test:
        t = time.perf_counter()
        preds.append(pb.validate(r["input"]))
        lat.append((time.perf_counter() - t) * 1000)
    systems[pb.name] = metrics(test, preds, lat)
    print(f"{pb.name}: 完全正确率 {pct(systems[pb.name]['full_correct'])}")

    # ---- 严格度档位（期望标签按 Balanced 定义，这里只看与档位无关的 FAR / FRR / 过度打扰率）
    profiles = {}
    v = Validator(db)
    for prof in ("STRICT", "BALANCED", "LENIENT"):
        preds, _, _ = run_validator(v, test, strictness=prof)
        m = metrics(test, preds)
        profiles[prof] = {k: m[k] for k in ("FAR", "FIX_recall", "FRR", "UCR", "silent_wrong")}
        profiles[prof]["accept_rate"] = sum(p[0] == ACCEPT for p in preds) / len(preds)

    # ---- 数据时效敏感性：从参考库中拿掉 500 个真实地址，模拟"新楼盘还没进库"
    rng = random.Random(7)
    uniq = [e for e in db.entities if len(db.by_blk_road[(e.blk, e.road_key)]) == 1]
    held = rng.sample(uniq, 500)
    db_stale = db.remove({e.eid for e in held})
    fresh_inputs = [f"{e.blk} {e.road.title()}, Singapore {e.postal}" for e in held]
    f1_rows = [r for r in test if r["category"] == "F1_nonexistent_block"]
    stale = {}
    for label, complete in (("assume_complete=True（默认：认为参考库完整）", True),
                            ("assume_complete=False（认为参考库可能不完整）", False)):
        vs = Validator(db_stale, Config(assume_complete=complete))
        acts = Counter(vs.validate(x).action for x in fresh_inputs)
        vf = Validator(db, Config(assume_complete=complete))
        f1_acts = Counter(vf.validate(r["input"]).action for r in f1_rows)
        stale[label] = {
            "new_address_fix_rate": acts[FIX] / len(fresh_inputs),
            "new_address_confirm_rate": acts[CONFIRM] / len(fresh_inputs),
            "nonexistent_fix_recall": f1_acts[FIX] / len(f1_rows),
            "nonexistent_accept_rate": f1_acts[ACCEPT] / len(f1_rows),
        }

    # ---- 本方案错例与混淆矩阵
    labels = [ACCEPT, CONFIRM, FIX]
    conf = {a: Counter() for a in labels}
    errors = defaultdict(list)
    for r, p, res in zip(test, ours_preds, ours_results):
        conf[r["expected_action"]][p[0]] += 1
        ok = p[0] == r["expected_action"] and (r["expected_action"] == FIX or p[1] == r["expected_eid"])
        if not ok:
            got = f"{res.entity.blk} {res.entity.road} {res.entity.postal}" if res.entity else "-"
            errors[r["category"]].append({"input": r["input"], "expected": f"{r['expected_action']} {r['expected_address']}".strip(),
                                          "got": f"{p[0]} {got}", "reasons": res.reasons, "note": r["note"]})
    unit_kept = [res.parsed.unit == r["expected_unit"] for r, res in zip(test, ours_results) if r["category"] == "I_with_unit"]

    out = {"systems": systems, "profiles": profiles, "staleness": stale,
           "confusion": {k: dict(v) for k, v in conf.items()}, "unit_kept_rate": sum(unit_kept) / len(unit_kept),
           "errors": {k: v[:5] for k, v in errors.items()}, "error_counts": {k: len(v) for k, v in errors.items()},
           "reference_entities": len(db.entities), "test_size": len(test), "dev_size": len(dev), "tag": args.tag}
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "eval_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(out)
    print(f"完成，用时 {time.time() - t0:.0f}s；报告：reports/eval_report.md")


def write_report(out: dict) -> None:
    S = out["systems"]
    order = ["本方案（Balanced）", "B1 模糊整串匹配（Geocoder 式）", "B2 仅查邮编",
             "消融：去掉邮编交叉校验", "消融：去掉道路拼写纠错", "消融：去掉楼宇名召回"]
    L = []
    L.append("# 评测报告（自动生成）\n")
    L.append(f"- 参考库：OneMap 新加坡邮编导出聚合的 {out['reference_entities']:,} 个地址实体")
    L.append(f"- 测试集：{out['test_size']:,} 条（10 类 × 400），开发集 {out['dev_size']:,} 条（仅用于调对照方案 B1 的阈值）")
    L.append("- 生成命令：`python scripts/make_golden_set.py && python scripts/evaluate.py`\n")

    L.append("## 1. 总览\n")
    L.append("| 方案 | 完全正确率 | 误收率 FAR ↓ | FIX 检出率 ↑ | 误拒率 FRR ↓ | 过度打扰率 ↓ | 地址正确率 ↑ | 静默错误率 ↓ | 单条延迟 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for name in order:
        m = S[name]
        lat = m.get("latency_ms", {})
        if "p95" in lat:
            ls = f"P50 {lat['p50']:.2f}ms / P95 {lat['p95']:.2f}ms"
        elif "mean_batched_4cores" in lat:
            ls = f"均摊 {lat['mean_batched_4cores']:.1f}ms（4 核批量）"
        else:
            ls = "-"
        L.append(f"| {name} | **{pct(m['full_correct'])}** | {pct(m['FAR'])} | {pct(m['FIX_recall'])} | {pct(m['FRR'])} | "
                 f"{pct(m['UCR'])} | {pct(m['addr_acc'])} | {pct(m['silent_wrong'])} | {ls} |")
    th = S["B1 模糊整串匹配（Geocoder 式）"].get("thresholds", {})
    L.append(f"\nB1 的阈值在开发集上网格搜索得到（accept ≥ {th.get('accept')}，confirm ≥ {th.get('confirm')}），已是对它最有利的设置。\n")

    L.append("## 2. 分类别完全正确率\n")
    L.append("| 类别 | 期望 | " + " | ".join(order) + " |")
    L.append("|---|---|" + "---|" * len(order))
    exp = {"A_clean": "ACCEPT", "B_messy_format": "ACCEPT", "C_street_typo": "CONFIRM", "D1_missing_postcode": "CONFIRM",
           "D2_missing_block": "FIX", "E_wrong_postcode": "CONFIRM", "F1_nonexistent_block": "FIX",
           "F2_nonexistent_street": "FIX", "G_building_name_only": "CONFIRM", "I_with_unit": "ACCEPT"}
    for c in CAT_ORDER:
        L.append(f"| {CAT_CN[c]} | {exp[c]} | " + " | ".join(pct(S[n]["per_category"].get(c, 0)) for n in order) + " |")
    L.append(f"\n本方案在 I 类中保留单元号的比例：{pct(out['unit_kept_rate'])}\n")

    L.append("## 3. 本方案混淆矩阵（行 = 期望，列 = 输出）\n")
    L.append("| 期望 \\ 输出 | ACCEPT | CONFIRM | FIX |")
    L.append("|---|---|---|---|")
    for a in (ACCEPT, CONFIRM, FIX):
        row = out["confusion"].get(a, {})
        L.append(f"| {a} | {row.get(ACCEPT, 0)} | {row.get(CONFIRM, 0)} | {row.get(FIX, 0)} |")

    L.append("\n## 4. 严格度档位\n")
    L.append("期望标签按 Balanced 定义，这里只比较与档位无关的风险指标。\n")
    L.append("| 档位 | 直接通过率 | 误收率 FAR | FIX 检出率 | 误拒率 FRR | 过度打扰率 | 静默错误率 |")
    L.append("|---|---|---|---|---|---|---|")
    for prof, m in out["profiles"].items():
        L.append(f"| {prof} | {pct(m['accept_rate'])} | {pct(m['FAR'])} | {pct(m['FIX_recall'])} | {pct(m['FRR'])} | "
                 f"{pct(m['UCR'])} | {pct(m['silent_wrong'])} |")

    L.append("\n## 5. 数据时效敏感性\n")
    L.append("从参考库中拿掉 500 个真实地址，模拟\"新楼盘尚未进库\"，看这些真实地址会被怎样判定；"
             "同时看 F1（楼栋号不存在）的检出率如何变化。\n")
    L.append("| 设置 | 新地址被判 FIX（误拒） | 新地址被判 CONFIRM | F1 不存在楼栋的 FIX 检出率 | F1 被判 ACCEPT |")
    L.append("|---|---|---|---|---|")
    for label, m in out["staleness"].items():
        L.append(f"| {label} | {pct(m['new_address_fix_rate'])} | {pct(m['new_address_confirm_rate'])} | "
                 f"{pct(m['nonexistent_fix_recall'])} | {pct(m['nonexistent_accept_rate'])} |")

    L.append("\n## 6. 本方案错例（每类最多 5 条）\n")
    for c in CAT_ORDER:
        errs = out["errors"].get(c, [])
        if not errs:
            continue
        L.append(f"**{CAT_CN[c]}**（共 {out['error_counts'][c]} 条错误）\n")
        L.append("| 输入 | 期望 | 输出 | 原因码 | 备注 |")
        L.append("|---|---|---|---|---|")
        for e in errs:
            L.append(f"| `{e['input']}` | {e['expected']} | {e['got']} | {', '.join(e['reasons'])} | {e['note']} |")
        L.append("")
    (ROOT / "reports" / "eval_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
