"""各市场评测：真实商户地址（留出的 20% POI）+ 合成地址（测试部分的道路），比较规则 / AI（CRF）/ 混合三种解析。

真实地址：输入 = 商户自填地址 + 城市 + 邮编（与结账表单一致），标准答案 = 商户坐标（弱标注）。结果与坐标一致才算对：
  门牌级（PREMISE）距离 ≤ 250 米（大宗地块的地址点与商户坐标可能相隔一两百米）；楼宇级 ≤ 400 米；
  道路级：该道路经过商户 250 米内；只到片区时判 FIX，片区中心在 3 公里内记为"判 FIX·片区对"
合成地址：按各市场写法渲染测试部分的道路（训练 AI 解析器时没见过这些道路名），标准答案已知。

结果分类：正确·直接通过 / 正确·要求确认 / 判 FIX / 错误建议（给错但要确认）/ 静默错误（给错且直接通过）

  python scripts/evaluate_markets.py [--markets AU,...] [--parsers rules,crf,hybrid] [--n 1000]
输出：reports/markets_eval.md、reports/markets_eval.json
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp.intl.engine import ACCEPT, ADD_SUB, CONFIRM, Engine, dist_to_street  # noqa: E402
from avmvp.intl.markets import MARKETS  # noqa: E402
from avmvp.intl.reference import DATA, MarketReference, center, haversine, is_test_place, number_key  # noqa: E402
from avmvp.intl.render import Renderer  # noqa: E402

DEV_START, TEST_START = 600, 1200
OUTCOMES = ["正确·直接通过", "正确·要求确认", "判 FIX·片区对", "判 FIX", "错误建议", "静默错误"]
CLASS_NAME = {"A": "A 类（有官方地址表）", "B": "B 类（中东）", "C": "C 类（没有开放地址表）"}


def real_cases(market: str, n: int, split: str = "test") -> list[dict]:
    rows = pq.read_table(DATA / market / "places.parquet", columns=["id", "addresses", "bbox"]).to_pylist()
    out = []
    for r in rows:
        if not is_test_place(r["id"]):
            continue
        a = (r["addresses"] or [{}])[0]
        ff = (a.get("freeform") or "").strip()
        if len(ff) < 5:
            continue
        text = ", ".join(x for x in (ff, (a.get("locality") or "").strip(), (a.get("postcode") or "").strip()) if x)
        lat, lng = center(r["bbox"])
        out.append({"input": text, "lat": lat, "lng": lng})
    random.Random(7).shuffle(out)
    # 固定切分（与 n 无关）：开发集是打乱后的第 600–1199 条，测试集从第 1200 条开始，两者永不重叠
    if split == "dev":
        return out[DEV_START:DEV_START + min(n, TEST_START - DEV_START)]
    return out[TEST_START:TEST_START + n]


def synthetic_cases(ref: MarketReference, n: int, split: str = "test") -> list[dict]:
    rd = Renderer(ref, "test", 11 if split == "test" else 12)
    out = []
    while len(out) < n:
        s = rd.sample(noise=0.3)
        if s is not None:
            out.append({"input": s.text, **s.truth})
    return out


def judge_real(eng: Engine, res, case) -> str:
    ok = False
    if res.lat is not None:
        d = haversine(res.lat, res.lng, case["lat"], case["lng"])
        if res.granularity == "PREMISE":
            ok = d <= 250
        elif res.granularity == "PREMISE_PROXIMITY":
            ok = d <= 400
        elif res.granularity == "ROUTE":
            ok = res.best is not None and res.best.street is not None and \
                dist_to_street(eng.ref, res.best.street, case["lat"], case["lng"]) <= 250
        elif res.granularity == "LOCALITY":
            ok = d <= 3000
    return _outcome(res.action, ok, res.granularity)


def error_m(eng: Engine, res, case) -> float | None:
    """给出的位置离标准答案多远（米）：道路级按道路到商户坐标的距离，其余按点距离。"""
    if res.lat is None:
        return None
    if res.granularity == "ROUTE" and res.best is not None and res.best.street is not None:
        return dist_to_street(eng.ref, res.best.street, case["lat"], case["lng"])
    return haversine(res.lat, res.lng, case["lat"], case["lng"])


def judge_synth(eng: Engine, res, case) -> str:
    ok = False
    b = res.best
    if b is not None:
        if "point" in case:
            # 同一门牌在地址表里可能有多个点（多个入口、芬兰文 / 瑞典文各一条、日本同一街区多个点）：门牌一致即可
            ok = b.point is not None and (b.point["id"] == case["point"] or (
                haversine(b.point["lat"], b.point["lng"], case["lat"], case["lng"]) <= 30) or (
                b.point["street"] == case["street"] and number_key(b.point["number"]) == number_key(case["number"] or "")))
            if not ok and b.point is None and b.street is not None and res.action != ACCEPT:
                ok = False
        elif b.street is not None:
            s1, s2 = eng.ref.streets[b.street], eng.ref.streets[case["street"]]
            ok = b.street == case["street"] or (s1.name == s2.name and haversine(s1.lat, s1.lng, s2.lat, s2.lng) < 800)
        elif b.building is not None:
            ok = dist_to_street(eng.ref, case["street"], b.building["lat"], b.building["lng"]) <= 300
    return _outcome(res.action, ok)


def _outcome(action: str, ok: bool, gran: str = "") -> str:
    if action == "FIX":
        return "判 FIX·片区对" if ok and gran == "LOCALITY" else "判 FIX"
    if ok:
        return "正确·直接通过" if action in (ACCEPT, ADD_SUB) else "正确·要求确认"
    return "静默错误" if action in (ACCEPT, ADD_SUB) else "错误建议"


def run(eng: Engine, cases: list[dict], judge) -> dict:
    t = time.perf_counter()
    oc, gran, dists, examples = Counter(), Counter(), [], {}
    gross = Counter()
    for c in cases:
        res = eng.validate(c["input"])
        o = judge(eng, res, c)
        oc[o] += 1
        gran[res.granularity] += 1
        if res.lat is not None and "lat" in c:
            dists.append(haversine(res.lat, res.lng, c["lat"], c["lng"]))
            err = error_m(eng, res, c)
            if o in ("静默错误", "错误建议") and err is not None and err > 1000:
                gross[o] += 1  # 偏差超过 1 公里：不是商户坐标不准能解释的
        if o in ("静默错误", "错误建议", "判 FIX") and len(examples.setdefault(o, [])) < 4:
            examples[o].append((c["input"][:90], res.action, res.granularity,
                                eng.to_response(res)["result"]["address"]["formattedAddress"][:70]))
    n = max(len(cases), 1)
    return {"n": len(cases), "outcomes": {k: oc[k] / n for k in OUTCOMES},
            "silent_over_1km": gross["静默错误"] / n, "wrong_over_1km": gross["错误建议"] / n,
            "granularity": {k: v / n for k, v in gran.most_common()},
            "median_error_m": statistics.median(dists) if dists else None,
            "within_500m": sum(d <= 500 for d in dists) / n,
            "ms": (time.perf_counter() - t) * 1000 / n, "examples": examples}


_LLM = None


def _llm(model_path: str | None):
    """本地小模型只加载一次（进程内 llama.cpp，占满 CPU，所以用小模型评测时 --jobs 1）。"""
    global _LLM
    if _LLM is None and model_path:
        from avmvp.intl.llm import CachedLLM, LlamaCppLLM
        name = Path(model_path).stem
        _LLM = CachedLLM(LlamaCppLLM(model_path), DATA.parent / "models" / f"cache_{name}.jsonl")
    return _LLM


def evaluate_market(code: str, parsers: list[str], n: int, split: str, llm_model: str | None = None,
                    real_only: bool = False) -> dict:
    ref = MarketReference.load(code)
    real = real_cases(code, n, split)
    synth = [] if real_only else synthetic_cases(ref, n, split)
    out = {}
    for parser in parsers:
        if parser not in ("rules", "llm") and not (DATA / code / "crf.model").exists():
            continue
        if parser == "llm":
            eng = Engine(code, "llm", ref, llm=_llm(llm_model))
        elif parser == "hybrid+llm":
            eng = Engine(code, "hybrid", ref, llm=_llm(llm_model))
        else:
            eng = Engine(code, parser, ref)
        r = out[parser] = {"real": run(eng, real, judge_real), "synthetic": run(eng, synth, judge_synth)}
        if eng.llm is not None:
            calls, secs = eng.llm.calls, eng.llm.seconds
            r["llm"] = {"model": eng.llm.llm.name, "calls": calls, "errors": eng.llm.errors,
                        "call_rate": calls / max(len(real) + len(synth), 1), "sec_per_call": secs / max(calls, 1)}
        ok = lambda x: 100 * (x["outcomes"]["正确·直接通过"] + x["outcomes"]["正确·要求确认"])  # noqa: E731
        print(f"{code} {parser:6} 真实：定位对 {ok(r['real']):.1f}% 直接通过且对 "
              f"{100 * r['real']['outcomes']['正确·直接通过']:.1f}% 静默 {100 * r['real']['outcomes']['静默错误']:.1f}%"
              f"（>1km {100 * r['real']['silent_over_1km']:.1f}%） | "
              f"合成：对 {ok(r['synthetic']):.1f}% 静默 {100 * r['synthetic']['outcomes']['静默错误']:.1f}%"
              f"（{r['real']['ms']:.0f} ms/条）", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", default=",".join(MARKETS))
    ap.add_argument("--parsers", default="rules,crf,hybrid")
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--tag", default="")
    ap.add_argument("--split", default="test", choices=["dev", "test"], help="dev 用于迭代，test 只在最后跑一次")
    ap.add_argument("--jobs", type=int, default=1, help="并行评测的市场数（每个进程约占 1–3 GB 内存）")
    ap.add_argument("--llm-model", help="本地小模型 GGUF 文件（parsers 里含 llm / hybrid+llm 时用）")
    ap.add_argument("--real-only", action="store_true", help="只评真实地址（小模型评测较慢时用）")
    args = ap.parse_args()
    codes, parsers = args.markets.split(","), args.parsers.split(",")
    job = [(c, parsers, args.n, args.split, args.llm_model, args.real_only) for c in codes]
    if args.jobs > 1:
        from multiprocessing import Pool
        with Pool(args.jobs) as pool:
            outs = pool.starmap(evaluate_market, job)
    else:
        outs = [evaluate_market(*j) for j in job]
    results = dict(zip(codes, outs))
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / f"markets_eval{args.tag}.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    write_report(results, args.tag)


def write_report(results: dict, tag: str) -> None:
    pct = lambda x: f"{100 * x:.1f}%"  # noqa: E731
    L = ["# 多市场评测报告（自动生成）\n",
         "- 真实地址：各城市留出的 20% 商户（不在参考库里）的自填地址，标准答案为商户坐标（弱标注）",
         "- 合成地址：按各市场写法渲染的测试部分道路（AI 解析器训练时没见过），标准答案已知",
         "- 解析方式：rules = 规则 + 地名表；crf = 机器学习（条件随机场）；hybrid = 两者都出候选，由参考数据裁决",
         "- 判对标准（真实地址）：门牌级 ≤ 250 米、楼宇级 ≤ 400 米、道路级为该道路经过商户 250 米内；"
         "\"偏差 >1 公里\"的静默错误不是商户坐标不准能解释的，是真正的错\n"]
    for kind, title in (("real", "真实商户地址"), ("synthetic", "合成地址")):
        L += [f"## {title}\n", "| 市场 | 类别 | 解析 | 条数 | 正确·直接通过 | 正确·要求确认 | 判 FIX·片区对 | 判 FIX | 错误建议 | "
              "静默错误 | 其中偏差 >1 公里 | 500 米内 | 毫秒/条 |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for code, per in results.items():
            m = MARKETS[code]
            for parser, r in per.items():
                x = r[kind]
                if not x["n"]:
                    continue
                o = x["outcomes"]
                L.append(f"| {m.name}（{code}） | {m.cls} | {parser} | {x['n']} | {pct(o['正确·直接通过'])} | "
                         f"{pct(o['正确·要求确认'])} | {pct(o['判 FIX·片区对'])} | {pct(o['判 FIX'])} | {pct(o['错误建议'])} | "
                         f"{pct(o['静默错误'])} | {pct(x.get('silent_over_1km', 0))} | {pct(x['within_500m'])} | "
                         f"{x['ms']:.0f} |")
        L.append("")
    llm_rows = [(code, parser, r["llm"]) for code, per in results.items() for parser, r in per.items() if "llm" in r]
    if llm_rows:
        L += ["## 本地小模型调用\n", "| 市场 | 解析 | 模型 | 调用次数 | 调用比例 | 秒/次 |", "|---|---|---|---|---|---|"]
        L += [f"| {MARKETS[c].name}（{c}） | {p} | {x['model']} | {x['calls']} | {pct(x['call_rate'])} | "
              f"{x['sec_per_call']:.1f} |" for c, p, x in llm_rows]
        L.append("")
    L.append("## 错误样例（规则解析，真实地址）\n")
    for code, per in results.items():
        ex = per.get("rules", {}).get("real", {}).get("examples", {})
        for o, items in ex.items():
            L.append(f"**{MARKETS[code].name} · {o}**\n")
            L += ["| 输入 | 结论 | 粒度 | 标准化结果 |", "|---|---|---|---|"]
            for t, a, g, f in items:
                L.append(f"| {t.replace('|', '/')} | {a} | {g} | {f.replace('|', '/')} |")
            L.append("")
    (ROOT / "reports" / f"markets_eval{tag}.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
