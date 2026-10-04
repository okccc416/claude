"""按市场校准"直接通过"的放宽规则：在开发集真实地址上统计各证据组合的准确率，足够可靠的组合才允许直接通过。

两类规则（其余情况仍按 engine._action 的默认规则）：
  A 类  PREMISE|POSTCODE_REPLACED        门牌由官方地址点确认、只有邮编被替换（萨格勒布通写 10000、立陶宛邮编细到路段）
  全部  POI|<几家商户印证>|<邮编是否印证>       门牌位置来自商户地址门牌点（官方表没有这个门牌，或没有官方表）
  全部  OSM|<邮编是否印证>|<是否唯一>|<名称怎么对上>  门牌位置来自 OSM 门牌点（官方表没有这个门牌，或没有官方表）
        没有官方表的市场，OSM / 商户门牌点没被放宽时按道路级规则决定，这些样本也计入对应的道路级组合
  B/C   ROUTE|<印证字段>|<是否唯一>|<名称怎么对上>
        道路级结论：默认要"邮编印证 + 道路名唯一 + 名称完全一致（或片区也印证）"，有的市场别的组合同样可靠
        （保加利亚多数地址不写 ul.，"邮编印证 + 唯一 + 去类型词一致"在开发集上 97% 正确）

允许的条件（开发集，每个组合单独统计）：样本 ≥ 25、正确率 ≥ 95%（Wilson 下界 ≥ 88%）、偏差超过 1 公里 ≤ 2%。

  python scripts/fit_accept_policy.py [--markets ...] [--jobs 3]
输出：models/accept_policy.json、reports/accept_policy.md
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from avmvp.intl.engine import Engine, policy_key_osm, policy_key_poi, policy_key_premise, policy_key_route  # noqa: E402
from avmvp.intl.markets import MARKETS  # noqa: E402
from evaluate_markets import error_m, judge_real, real_cases  # noqa: E402

MIN_N, MIN_OK, MIN_LOWER, MAX_GROSS = 25, 0.95, 0.88, 0.02
BLOCKING = ("AMBIGUOUS_MULTIPLE_CANDIDATES", "MISSING_PREMISE")


def wilson_lower(k: int, n: int, z: float = 1.96) -> float:
    if not n:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def add(stats: dict, key: str, eng, res, case) -> None:
    ok = judge_real(eng, res, case).startswith("正确")
    err = error_m(eng, res, case)
    s = stats[key]
    s[0] += 1
    s[1] += ok
    s[2] += (not ok) and err is not None and err > 1000


def collect(code: str) -> dict:
    eng = Engine(code, "hybrid" if (eng_dir := ROOT / "data" / "markets" / code / "crf.model").exists() else "rules",
                 policy={})
    stats: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for c in real_cases(code, 600, "dev"):
        res = eng.validate(c["input"])
        b = res.best
        if b is None or any(r in res.reasons for r in BLOCKING):
            continue
        key = None
        route_rules = res.parsed.number and "ROUTE_NOT_CORROBORATED" in res.reasons and not (
            {"STREET_SPELL_CORRECTED", "STREET_PARTIAL_MATCH", "AREA_STREET_MISMATCH", "POSTCODE_STREET_MISMATCH"}
            & set(res.reasons))
        if not eng.ref.has_addresses and route_rules and res.granularity != "ROUTE" and (
                {"PREMISE_FROM_OSM", "PREMISE_INTERPOLATED", "PREMISE_FROM_POI"} & set(res.reasons)):
            # 没有官方表的市场：OSM / 商户门牌点不够可靠时引擎按道路级规则决定，道路级组合也要按这些样本统计
            add(stats, policy_key_route(b), eng, res, c)
        if res.granularity == "PREMISE_PROXIMITY" and "PREMISE_FROM_POI" in res.reasons and not (
                {"STREET_SPELL_CORRECTED", "STREET_PARTIAL_MATCH", "AREA_STREET_MISMATCH", "POSTCODE_STREET_MISMATCH",
                 "POSTCODE_REPLACED", "POSTCODE_NOT_FOUND", "STREET_INFERRED"} & set(res.reasons)):
            key = policy_key_poi(b)
        elif res.granularity == "PREMISE" and "PREMISE_FROM_OSM" in res.reasons:
            if not ({"STREET_SPELL_CORRECTED", "STREET_PARTIAL_MATCH", "AREA_STREET_MISMATCH", "POSTCODE_STREET_MISMATCH",
                     "POSTCODE_REPLACED", "POSTCODE_NOT_FOUND", "STREET_INFERRED"} & set(res.reasons)):
                key = policy_key_osm(b)
        elif eng.ref.has_addresses and res.granularity == "PREMISE":
            key = policy_key_premise(b)
        elif not eng.ref.has_addresses and res.granularity == "ROUTE" and route_rules:
            key = policy_key_route(b)
        if key is not None:
            add(stats, key, eng, res, c)
    print(f"{code} done", flush=True)
    return dict(stats)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", default=",".join(MARKETS))
    ap.add_argument("--jobs", type=int, default=3)
    args = ap.parse_args()
    codes = args.markets.split(",")
    if args.jobs > 1:
        from multiprocessing import Pool
        with Pool(args.jobs) as pool:
            outs = pool.map(collect, codes)
    else:
        outs = [collect(c) for c in codes]
    allow: dict[str, list[str]] = {}
    L = ["# 直接通过的放宽规则（开发集校准，自动生成）\n",
         f"条件：样本 ≥ {MIN_N}、正确率 ≥ {MIN_OK:.0%}（Wilson 下界 ≥ {MIN_LOWER:.0%}）、偏差 >1 公里 ≤ {MAX_GROSS:.0%}。"
         "未列出的组合仍按默认规则（A 类邮编被替换 -> 要求确认；B / C 类道路级要邮编印证 + 道路名唯一 + 名称完全一致）。\n",
         "| 市场 | 证据组合 | 样本 | 正确 | 偏差 >1 公里 | 允许直接通过 |", "|---|---|---|---|---|---|"]
    for code, stats in zip(codes, outs):
        for key, (n, ok, gross) in sorted(stats.items(), key=lambda x: -x[1][0]):
            good = n >= MIN_N and ok / n >= MIN_OK and wilson_lower(ok, n) >= MIN_LOWER and gross / n <= MAX_GROSS
            if good:
                allow.setdefault(code, []).append(key)
            if n >= 10:
                L.append(f"| {MARKETS[code].name}（{code}） | {key} | {n} | {ok / n:.1%} | {gross / n:.1%} | "
                         f"{'是' if good else ''} |")
    path = ROOT / "models" / "accept_policy.json"
    old = json.loads(path.read_text(encoding="utf-8")).get("allow", {}) if path.exists() else {}
    old = {k: v for k, v in old.items() if k not in codes}  # 只重算这次指定的市场
    path.write_text(json.dumps({"criteria": {"min_n": MIN_N, "min_ok": MIN_OK, "min_wilson_lower": MIN_LOWER,
                                             "max_over_1km": MAX_GROSS}, "allow": {**old, **allow}},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "reports" / "accept_policy.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(json.dumps(allow, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
