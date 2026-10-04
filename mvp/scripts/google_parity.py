"""与 Google Address Validation 的差距：Google 覆盖的市场（美国除外）上，估算 Google 在同一测试集上能达到的上限，
看我们差多少。

我们拿不到 Google 的结果（服务条款也不允许用它的输出改进竞品），所以按 Google 公开的判定规则
（developers.google.com/maps/documentation/address-validation/build-validation-logic）估一个上限：
  - 输入里没有门牌号也没有楼名：Google 会把 street_number 列进 missingComponentTypes，判 FIX
    -> 这部分 Google 同样"定位不对"（按我们的判对口径，FIX 不算定位对）
  - 标注噪声：输入的"道路 + 门牌"与地址点原样一致，但商户坐标离这个地址点超过 250 米
    -> Google 同样会定位到这个地址，按商户坐标同样判错。地址点指官方地址表；有官方表的市场里只有 OSM 有的门牌要求邮编也一致，
    没有官方表的市场 OSM 门牌点就是最好的门牌数据。没有官方地址表的市场按 A 类市场噪声比例的中位数估计，
    OSM 门牌点上实测的比例更高时取实测值
  - 英国（没有官方地址表，但有官方一户一码邮编中心 Code-Point Open）：所写道路经过所写邮编的中心（300 米内），
    而商户坐标离这个邮编中心超过 500 米，同样算标注噪声
  - 其余样本：Google 的数据近乎完整，按全部做对估计（这是对 Google 偏乐观的上限，所以差距是保守估计）

差距 = 上限 − 我们的"定位对"比例。差距 ≤ 3 个百分点视为与 Google 持平（在弱标注和抽样误差范围内）。

  python scripts/google_parity.py [--split test] [--jobs 3]
输出：reports/google_parity.md、reports/google_parity.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from avmvp.intl.engine import ACCEPT, ADD_SUB, Engine, dist_to_street  # noqa: E402
from avmvp.intl.reference import OSM_ID_BASE, haversine  # noqa: E402
from avmvp.intl.markets import MARKETS  # noqa: E402
from evaluate_markets import error_m, judge_real, real_cases  # noqa: E402

# Google AV 覆盖的国家 / 地区（2026-09-28 官方页面；美国除外，新加坡另有专用引擎和评测，见 docs/07、11）
GOOGLE = ["AU", "NZ", "JP", "IN", "CA", "MX", "PR", "BR", "AR", "CL", "CO", "GB", "IE", "DE", "FR", "NL", "BE", "LU",
          "CH", "AT", "IT", "ES", "PT", "DK", "SE", "NO", "FI", "EE", "LV", "LT", "PL", "CZ", "SK", "HU", "SI", "HR",
          "BG", "MY"]
PARITY_GAP = 0.03


def postcode_points(code: str) -> dict:
    """一户一码市场的官方邮编中心点（英国 Code-Point Open，每个邮编约 15 户）：fetch_extra_addresses.py 生成，只用于估计标注噪声。"""
    path = ROOT / "data" / "markets" / code / "postcode_points.parquet"
    if not path.exists():
        return {}
    import pyarrow.parquet as pq
    return {r["postcode"].replace(" ", ""): (r["lat"], r["lng"]) for r in pq.read_table(path).to_pylist()}


def _postcode_noise(eng: Engine, r, case: dict, pc_points: dict) -> bool:
    """标注噪声的另一种判定（没有官方地址表、但有官方一户一码邮编中心的市场）：所写道路经过所写邮编的中心（300 米内，
    道路与邮编相互印证），而商户坐标离这个邮编中心超过 500 米。与地址点判定同理：Google 会定位到这个地址，同样判错。"""
    p = r.parsed
    pt = pc_points.get((p.postcode or "").replace(" ", ""))
    if pt is None or r.best is None or r.best.street is None:
        return False
    return haversine(pt[0], pt[1], case["lat"], case["lng"]) > 500 and dist_to_street(eng.ref, r.best.street, *pt) <= 300


def classify(code: str, split: str, n: int) -> dict:
    eng = Engine(code, "hybrid")
    pc_points = postcode_points(code)
    c: Counter = Counter()
    for case in real_cases(code, n, split):
        r = eng.validate(case["input"])
        ok = judge_real(eng, r, case).startswith("正确")
        err = error_m(eng, r, case)
        p = r.parsed
        if ok:
            c["ok"] += 1
            c["accept_ok"] += r.action in (ACCEPT, ADD_SUB)
        elif r.granularity == "PREMISE" and r.best and r.best.point and (
                r.best.point["id"] < OSM_ID_BASE or not eng.ref.has_addresses
                or (p.postcode and r.best.point["postcode"] == p.postcode)) \
                and r.best.street_span is not None and r.best.street_span.how in ("exact", "core") and err and err > 250:
            c["noise"] += 1
        elif not p.number and not (r.best and r.best.building) and not p.codes:
            c["no_premise"] += 1
        elif pc_points and _postcode_noise(eng, r, case, pc_points):
            c["noise"] += 1
            c["noise_postcode"] += 1
        else:
            c["miss"] += 1
            # 差在哪：道路都没找到 / 道路找到了但门牌位置没给对 / 给了位置但不对
            c["miss_nothing" if r.best is None else "miss_number" if "PREMISE_NOT_FOUND" in r.reasons
              else "miss_wrong"] += 1
        c["n"] += 1
    print(f"{code} done", flush=True)
    return dict(c)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=["dev", "test"])
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--markets", default=",".join(GOOGLE))
    args = ap.parse_args()
    codes = args.markets.split(",")
    n = args.n if args.split == "test" else min(args.n, 600)
    if args.jobs > 1:
        from multiprocessing import Pool
        with Pool(args.jobs) as pool:
            outs = pool.starmap(classify, [(c, args.split, n) for c in codes])
    else:
        outs = [classify(c, args.split, n) for c in codes]
    keys = ("n", "ok", "accept_ok", "noise", "noise_postcode", "no_premise", "miss", "miss_nothing", "miss_number",
            "miss_wrong")
    res = {c: {k: o.get(k, 0) for k in keys} for c, o in zip(codes, outs)}
    a_noise = statistics.median(r["noise"] / r["n"] for c, r in res.items() if MARKETS[c].cls == "A")
    rows = []
    for c, r in res.items():
        N = r["n"]
        # 没有官方地址表的市场：按 A 类中位数估计；OSM 门牌点上实测到的噪声更高时取实测值（实测只覆盖有 OSM 门牌的样本，是下限）
        noise = r["noise"] / N if MARKETS[c].cls == "A" else max(a_noise, r["noise"] / N)
        ceiling = 1 - r["no_premise"] / N - noise
        ours = r["ok"] / N
        rows.append((c, N, ours, r["accept_ok"] / N, r["no_premise"] / N, noise, ceiling, ceiling - ours,
                     r.get("miss_nothing", 0) / N, r.get("miss_number", 0) / N, r.get("miss_wrong", 0) / N))
    rows.sort(key=lambda x: x[7])
    par = sum(x[7] <= PARITY_GAP for x in rows)
    L = ["# 与 Google Address Validation 的差距（自动生成）\n",
         f"- 数据：{'测试集' if args.split == 'test' else '开发集'}真实商户地址，每个市场 {n} 条；Google 覆盖的 {len(rows)} 个国家 / 地区（美国除外）",
         "- Google 上限 = 1 − 没有门牌也没有楼名的比例（Google 判 FIX）− 标注噪声比例（地址点原样一致但商户坐标偏离 > 250 米；"
         f"没有官方地址表的市场按 A 类中位数 {a_noise:.1%} 估计，OSM 门牌点上实测更高时取实测值；英国另按官方一户一码邮编中心判定："
         "所写道路经过邮编中心而商户坐标离它 > 500 米）。其余样本按 Google 全部做对估计，所以差距是保守估计",
         f"- 差距 ≤ {PARITY_GAP:.0%} 视为持平：**{par} / {len(rows)} 个市场持平**\n",
         "| 市场 | 类别 | 条数 | 我们：定位对 | 我们：直接通过且对 | 无门牌（Google 判 FIX） | 标注噪声 | Google 上限（估计） | 差距 | 持平 "
         "| 没做对的：道路没找到 | 门牌不在库里 | 位置给错 |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c, N, ours, acc, nop, noise, ceil, gap, m1, m2, m3 in rows:
        L.append(f"| {MARKETS[c].name}（{c}） | {MARKETS[c].cls} | {N} | {ours:.1%} | {acc:.1%} | {nop:.1%} | {noise:.1%} | "
                 f"{ceil:.1%} | {gap:+.1%} | {'是' if gap <= PARITY_GAP else ''} | {m1:.1%} | {m2:.1%} | {m3:.1%} |")
    tag = "" if args.split == "test" else "_dev"
    (ROOT / "reports" / f"google_parity{tag}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (ROOT / "reports" / f"google_parity{tag}.json").write_text(json.dumps(
        {"a_noise_median": a_noise, "markets": res}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(L[-len(rows):]))


if __name__ == "__main__":
    main()
