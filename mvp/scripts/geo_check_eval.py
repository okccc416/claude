"""geo 核对层的模拟评测：在开发集真实输入上，按参考库构造 geo 服务可能给出的几种结果，看核对层能否
"对的直接用、错的拦下来"。

取开发集里本引擎定位到官方 / OSM 门牌点而且定位对的真实地址（这条门牌点当作标准答案 R），构造 6 种 geo 返回
（Google 地理编码格式）：
  正确          R 本身
  门牌吸附错    同一条路上离 R 150 米以上的另一个门牌
  同名路选错    2 公里外同名道路上的门牌（优先同号）
  相邻路选错    R 附近 150–800 米、另一条路上的门牌
  只到道路级    R 所在道路的中心点，没有门牌（GEOMETRIC_CENTER）
  没有结果      空
指标：直接通过的比例、直接通过但离 R 超过 250 米（误放行）、最终位置离 R 不超过 250 米（geo 错时靠本引擎找回）。
真实 geo 的出错分布未知，这里只验证核对逻辑。

拿到 geo 服务对测试集的真实返回后：
  1. python scripts/geo_check_eval.py --export data/geo_requests.jsonl      # 导出测试集输入（不含标注）给 geo 跑
  2. geo 那边逐行返回 {"id": ..., "geo": <geo 服务的原始响应>}，存成 JSONL
  3. python scripts/geo_check_eval.py --geo-file geo_results.jsonl          # 按市场对比：只用 geo / 只用本引擎 / geo + 核对
     输出 reports/geo_real_eval.md

  python scripts/geo_check_eval.py [--markets DE,FR,...] [--n 60] [--jobs 4]
输出：reports/geo_check_eval.md、reports/geo_check_eval.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from avmvp.intl.engine import ACCEPT, Engine  # noqa: E402
from avmvp.intl.geo_check import validate_with_geo  # noqa: E402
from avmvp.intl.markets import MARKETS  # noqa: E402
from avmvp.intl.reference import haversine  # noqa: E402
from avmvp.intl.text import key  # noqa: E402
from evaluate_markets import judge_real, real_cases  # noqa: E402

DEFAULT = "DE,FR,ES,IT,NL,BE,AT,CH,PL,CZ,PT,BR,MX,CL,AU,CA,GB"
KINDS = ("正确", "门牌吸附错", "同名路选错", "相邻路选错", "只到道路级", "没有结果")
COLS = ("id", "number", "street", "unit", "postcode", "locality", "lat", "lng")


def geo_json(ref, pt: dict | None, street: int | None = None, number: bool = True) -> dict:
    if pt is None and street is None:
        return {"results": []}
    sid = pt["street"] if pt else street
    s = ref.streets[sid]
    comps = [{"long_name": pt["number"], "types": ["street_number"]}] if pt and number else []
    comps.append({"long_name": s.name, "types": ["route"]})
    if pt and pt.get("locality"):
        comps.append({"long_name": pt["locality"], "types": ["locality"]})
    if pt and pt.get("postcode") and number:
        comps.append({"long_name": pt["postcode"], "types": ["postal_code"]})
    lat, lng = (pt["lat"], pt["lng"]) if pt and number else (s.lat, s.lng)
    return {"results": [{"address_components": comps, "geometry": {
        "location": {"lat": lat, "lng": lng}, "location_type": "ROOFTOP" if number and pt else "GEOMETRIC_CENTER"}}]}


def variants(eng: Engine, r: dict, rnd: random.Random) -> dict[str, dict | None]:
    ref, db = eng.ref, eng.ref.db
    out: dict[str, dict | None] = {"正确": r, "没有结果": None}
    rows = [dict(zip(COLS, x)) for x in db.execute(f"SELECT {', '.join(COLS)} FROM addr WHERE street=? LIMIT 400",
                                                   (r["street"],))]
    rows = [x for x in rows if x["number"] != r["number"] and haversine(x["lat"], x["lng"], r["lat"], r["lng"]) > 150]
    out["门牌吸附错"] = rnd.choice(rows) if rows else None
    k = " ".join(key(ref.streets[r["street"]].name, eng.market).split())
    from avmvp.intl.engine import dist_to_street
    others = [sid for sid in ref.street_keys.get(k, ()) if sid != r["street"]
              and dist_to_street(ref, sid, r["lat"], r["lng"]) > 2000]
    cand = []
    for sid in others[:20]:
        cand += [dict(zip(COLS, x)) for x in db.execute(
            f"SELECT {', '.join(COLS)} FROM addr WHERE street=? ORDER BY number_key != ? LIMIT 5", (sid, r["number"]))]
    out["同名路选错"] = cand[0] if cand else None
    d = 0.008
    near = [dict(zip(COLS, x)) for x in db.execute(
        f"SELECT {', '.join(COLS)} FROM addr WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ? AND street != ? LIMIT 400",
        (r["lat"] - d, r["lat"] + d, r["lng"] - d, r["lng"] + d, r["street"]))]
    near = [x for x in near if 150 < haversine(x["lat"], x["lng"], r["lat"], r["lng"]) < 800
            and " ".join(key(ref.streets[x["street"]].name, eng.market).split()) != k]
    out["相邻路选错"] = rnd.choice(near) if near else None
    out["只到道路级"] = "STREET"
    return out


def run(code: str, n: int) -> dict:
    eng = Engine(code, "hybrid")
    rnd = random.Random(11)
    res: dict[str, Counter] = {k: Counter() for k in KINDS}
    base = 0
    for case in real_cases(code, 600, "dev"):
        ours = eng.validate(case["input"])
        if not (ours.granularity == "PREMISE" and ours.best and ours.best.point and ours.best.point["street"] is not None
                and judge_real(eng, ours, case).startswith("正确")):
            continue
        r = ours.best.point
        base += 1
        for kind, pt in variants(eng, r, rnd).items():
            if kind != "没有结果" and pt is None:
                continue
            geo = geo_json(eng.ref, None, r["street"], number=False) if pt == "STREET" else geo_json(eng.ref, pt)
            for mode, use in (("", True), ("blind:", False)):
                out = validate_with_geo(eng, case["input"], geo, use_engine=use)
                c = res[kind]
                ok = out.lat is not None and haversine(out.lat, out.lng, r["lat"], r["lng"]) <= 250
                c[mode + "n"] += 1
                c[mode + "final_ok"] += ok
                c[mode + "accept"] += out.action == ACCEPT
                c[mode + "false_accept"] += out.action == ACCEPT and not ok
                c[mode + "confirm"] += out.action != ACCEPT and out.action != "FIX"
                c[mode + "fix"] += out.action == "FIX"
                if not mode:
                    c["geo_ok"] += kind == "正确"  # 只用 geo、不核对：只有"正确"这一种对
                for r_ in out.reasons if not mode else []:
                    if r_.startswith("GEO_"):
                        c["r:" + r_] += 1
        if base >= n:
            break
    print(f"{code} done ({base})", flush=True)
    return {"n": base, "kinds": {k: dict(v) for k, v in res.items()}}


# ---------------------------------------------------------------------------------------------- 真实 geo 返回
def export(path: str, codes: list[str], n: int) -> None:
    rows = 0
    with open(path, "w", encoding="utf-8") as f:
        for code in codes:
            for i, case in enumerate(real_cases(code, n, "test")):
                f.write(json.dumps({"id": f"{code}-{i}", "regionCode": code, "input": case["input"]},
                                   ensure_ascii=False) + "\n")
                rows += 1
    print(f"导出 {rows:,} 条到 {path}")


def run_real(code: str, n: int, geo: dict) -> dict:
    from avmvp.intl.geo_check import parse_geo
    eng = Engine(code, "hybrid")
    c = Counter()
    for i, case in enumerate(real_cases(code, n, "test")):
        g = geo.get(f"{code}-{i}")
        if g is None:
            continue
        c["n"] += 1
        pts = parse_geo(g)
        c["geo_has"] += bool(pts)
        c["geo_ok"] += bool(pts) and haversine(pts[0].lat, pts[0].lng, case["lat"], case["lng"]) <= 250
        ours = eng.validate(case["input"])
        c["ours_ok"] += judge_real(eng, ours, case).startswith("正确")
        c["ours_accept"] += ours.action == ACCEPT
        c["ours_silent"] += judge_real(eng, ours, case) == "静默错误"
        both = validate_with_geo(eng, case["input"], g)
        ok = both.lat is not None and haversine(both.lat, both.lng, case["lat"], case["lng"]) <= (
            250 if both.granularity == "PREMISE" else 400 if both.granularity == "PREMISE_PROXIMITY" else 1000)
        c["both_ok"] += ok
        c["both_accept"] += both.action == ACCEPT
        c["both_silent"] += both.action == ACCEPT and not ok
    print(f"{code} done", flush=True)
    return dict(c)


def main_real(path: str, codes: list[str], n: int, jobs: int) -> None:
    geo = {}
    for line in open(path, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            geo[r["id"]] = r.get("geo")
    codes = [c for c in codes if any(k.startswith(c + "-") for k in geo)]
    from multiprocessing import Pool
    with Pool(jobs) as pool:
        outs = pool.starmap(run_real, [(c, n, geo) for c in codes])
    L = ["# geo 服务真实返回的对比（测试集，自动生成）\n",
         "- 定位对：离商户坐标不超过 250 米（门牌附近 400 米、道路级 1 公里）；静默错误：直接通过但位置不对",
         "- 只用 geo：直接采用 geo 的第一条结果；geo + 核对：geo 的门址代回输入核对，对不上时用本引擎（intl/geo_check.py）\n",
         "| 市场 | 条数 | geo 有结果 | 只用 geo：定位对 | 本引擎：定位对 | 本引擎：直接通过 / 静默错误 | geo + 核对：定位对 | "
         "geo + 核对：直接通过 / 静默错误 |", "|---|---|---|---|---|---|---|---|"]
    for code, c in zip(codes, outs):
        N = c.get("n", 0) or 1
        L.append(f"| {MARKETS[code].name}（{code}） | {c.get('n', 0)} | {c.get('geo_has', 0) / N:.1%} | {c.get('geo_ok', 0) / N:.1%} | "
                 f"{c.get('ours_ok', 0) / N:.1%} | {c.get('ours_accept', 0) / N:.1%} / {c.get('ours_silent', 0) / N:.1%} | "
                 f"{c.get('both_ok', 0) / N:.1%} | {c.get('both_accept', 0) / N:.1%} / {c.get('both_silent', 0) / N:.1%} |")
    (ROOT / "reports" / "geo_real_eval.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", default=DEFAULT)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--export", help="导出测试集输入（JSONL：id、regionCode、input）给 geo 服务跑")
    ap.add_argument("--geo-file", help="geo 服务对导出输入的返回（JSONL：id、geo）")
    ap.add_argument("--n-test", type=int, default=1000)
    args = ap.parse_args()
    codes = args.markets.split(",")
    if args.export:
        all_codes = [c for c in MARKETS if c != "SG"] if args.markets == DEFAULT else codes
        return export(args.export, all_codes, args.n_test)
    if args.geo_file:
        all_codes = [c for c in MARKETS if c != "SG"] if args.markets == DEFAULT else codes
        return main_real(args.geo_file, all_codes, args.n_test, args.jobs)
    from multiprocessing import Pool
    with Pool(args.jobs) as pool:
        outs = pool.starmap(run, [(c, args.n) for c in codes])
    res = dict(zip(codes, outs))
    (ROOT / "reports" / "geo_check_eval.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    L = ["# geo 核对层（模拟评测，自动生成）\n",
         f"- {len(codes)} 个市场（{', '.join(codes)}）开发集真实输入，每个市场取本引擎定位到门牌点而且定位对的 {args.n} 条，"
         "这条门牌点当作标准答案 R；按参考库构造 geo 可能给出的几种结果（见脚本说明），核对后看结论",
         "- 直接通过：结论 ACCEPT；误放行：直接通过但离 R 超过 250 米；最终对：最终位置离 R 不超过 250 米"
         "（geo 错时靠本引擎找回）；只用 geo：不核对、直接采用 geo 的结果时的正确率\n",
         "**核对层 + 本引擎**（线上的用法：geo 错时本引擎重新召回）：\n",
         "| geo 返回 | 样本 | 直接通过 | 误放行 | 最终对 | 只用 geo | 主要原因码 |", "|---|---|---|---|---|---|---|"]
    tots = {}
    for k in KINDS:
        tot = Counter()
        for r in res.values():
            tot.update(r["kinds"].get(k, {}))
        tots[k] = tot
        n = tot["n"] or 1
        top = ", ".join(f"{c[2:]} {v / n:.0%}" for c, v in tot.most_common() if c.startswith("r:"))[:160]
        L.append(f"| {k} | {tot['n']} | {tot['accept'] / n:.1%} | {tot['false_accept'] / n:.1%} | {tot['final_ok'] / n:.1%} | "
                 f"{tot['geo_ok'] / n:.0%} | {top} |")
    L += ["\n**只有核对层**（假装本引擎什么都没找到：参考库没覆盖的地方，只能靠核对层把关）：\n",
          "| geo 返回 | 样本 | 直接通过 | 误放行 | 请用户确认 | 请用户补充 | 最终对 |", "|---|---|---|---|---|---|---|"]
    for k in KINDS:
        t = tots[k]
        n = t["blind:n"] or 1
        L.append(f"| {k} | {t['blind:n']} | {t['blind:accept'] / n:.1%} | {t['blind:false_accept'] / n:.1%} | "
                 f"{t['blind:confirm'] / n:.1%} | {t['blind:fix'] / n:.1%} | {t['blind:final_ok'] / n:.1%} |")
    L += ["\n**按市场（只有核对层）：geo 正确时的直接通过率 / geo 错误（吸附错 + 同名路 + 相邻路）时的误放行率**\n",
          "| 市场 | 样本 | geo 正确时直接通过 | geo 错误时误放行 |", "|---|---|---|---|"]
    for c, r in res.items():
        ok = r["kinds"]["正确"]
        bad = Counter()
        for k in ("门牌吸附错", "同名路选错", "相邻路选错"):
            bad.update(r["kinds"].get(k, {}))
        L.append(f"| {MARKETS[c].name}（{c}） | {r['n']} | {ok.get('blind:accept', 0) / max(ok.get('blind:n', 0), 1):.0%} | "
                 f"{bad['blind:false_accept'] / max(bad['blind:n'], 1):.1%}（{bad['blind:n']} 条） |")
    (ROOT / "reports" / "geo_check_eval.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
