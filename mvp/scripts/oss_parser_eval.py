"""开源地址解析器对比：libpostal（openvenues，MIT）与本方案的解析（规则 + CRF）。

做法：只换解析这一步，召回和验真用同一套参考库和判定规则，所以差别全部来自"字段拆得对不对"。
  hybrid        本方案（规则 + CRF，上线配置）
  libpostal     libpostal 拆出的门牌 / 道路 / 片区 / 楼名 / 邮编 / 单元 -> 本方案的参考库查找与判定
  hybrid+lp     本方案没能直接通过时，再用 libpostal 拆一次（与本地小模型的级联同一机制），参考数据裁决
libpostal 的结果和 CRF 一样不改写原文，所以不套用小模型的"最多 CONFIRM"上限。

数据：各市场开发集的真实商户地址（evaluate_markets.py 同一套）和合成地址；可选 --responses：真实流量包
（0924，每条有用户输入和目标坐标），只评本方案 44 个市场的部分、不看 geo，距离目标 ≤ 100 米算定位对。

需要先装好 libpostal 和 Python 绑定 postal（见 mvp/README.md），绑定不在默认路径时用 --postal-path。
  python scripts/oss_parser_eval.py [--markets AU,DE] [--n 600] [--responses 0924.jsonl] [--jobs 3]
输出：reports/oss_parser_eval.md、reports/oss_parser_eval.json（只有汇总数字）
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from avmvp.intl.engine import ACCEPT, CONFIRM, Engine  # noqa: E402
from avmvp.intl.llm import FIELDS, LLMParser  # noqa: E402
from avmvp.intl.markets import MARKETS  # noqa: E402
from avmvp.intl.reference import MarketReference, haversine  # noqa: E402
from evaluate_markets import OUTCOMES, judge_real, judge_synth, real_cases, synthetic_cases  # noqa: E402

CONFIGS = ["hybrid", "libpostal", "hybrid+lp"]
_NUM_MARK = re.compile(r"^(?:#|n[º°o]\.?|no\.?|nr\.?|num\.?)\s*", re.I)


class LibpostalExtractor:
    """libpostal 的标签 -> 与本地小模型相同的六个字段。"""
    name = "libpostal"

    def __init__(self):
        from postal.parser import parse_address
        self._parse = parse_address

    def extract(self, text: str, market: str) -> dict:
        out = {k: "" for k in FIELDS}
        units = []
        for val, lab in self._parse(text):  # 只给国家不给语言时绑定会报错；解析模型本身不依赖国家
            if lab == "house_number" and not out["house_number"]:
                out["house_number"] = _NUM_MARK.sub("", val)
            elif lab == "road" and not out["street"]:
                out["street"] = val
            elif lab in ("unit", "level", "staircase", "entrance"):
                units.append(val)
            elif lab == "house" and not out["building"]:
                out["building"] = val
            elif lab in ("suburb", "city_district") and not out["area"]:
                out["area"] = val
            elif lab == "postcode" and not out["postcode"]:
                out["postcode"] = val
        out["unit"] = " ".join(units)
        return out


class LibpostalParser(LLMParser):
    name = "libpostal"


class NoCapEngine(Engine):
    """libpostal 与 CRF 一样不改写原文：不套用本地小模型的结论上限。"""

    def _llm_cap(self, res):
        return res


_EXTRACTOR = None


def _init(postal_path: str | None) -> None:
    global _EXTRACTOR
    if postal_path:
        sys.path.insert(0, postal_path)
    _EXTRACTOR = LibpostalExtractor()
    _EXTRACTOR.extract("1 Main Street", "AU")  # 先加载模型（约 10 秒、2 GB 内存）


def engines(code: str, ref: MarketReference) -> dict[str, Engine]:
    out = {"hybrid": Engine(code, "hybrid", ref)}
    for name, parser in (("libpostal", "llm"), ("hybrid+lp", "hybrid")):
        eng = NoCapEngine(code, parser, ref, llm=_EXTRACTOR)
        eng.llm = LibpostalParser(ref, _EXTRACTOR)
        out[name] = eng
    return out


def run(eng: Engine, cases: list[dict], judge) -> dict:
    oc = Counter()
    t = time.perf_counter()
    for c in cases:
        oc[judge(eng, eng.validate(c["input"]), c)] += 1
    n = max(len(cases), 1)
    return {"n": len(cases), "outcomes": {k: oc[k] / n for k in OUTCOMES}, "ms": (time.perf_counter() - t) * 1000 / n}


def evaluate_market(job: tuple) -> tuple[str, dict]:
    code, n, split = job
    ref = MarketReference.load(code)
    real, synth = real_cases(code, n, split), synthetic_cases(ref, n, split)
    out = {}
    for name, eng in engines(code, ref).items():
        out[name] = {"real": run(eng, real, judge_real), "synthetic": run(eng, synth, judge_synth)}
    ok = lambda r: 100 * (r["outcomes"]["正确·直接通过"] + r["outcomes"]["正确·要求确认"])  # noqa: E731
    print(code, " | ".join(f"{k} 真实 {ok(v['real']):.1f}% 合成 {ok(v['synthetic']):.1f}%" for k, v in out.items()),
          flush=True)
    return code, out


def evaluate_traffic(path: str) -> dict:
    """真实流量包：本方案 44 个市场的查询，不看 geo，只比解析。"""
    from geo_real_eval import ISO3
    rows = [json.loads(x) for x in open(path, encoding="utf-8")]
    by_cc = defaultdict(list)
    for r in rows:
        cc = ISO3.get(r["source_id"].split(":")[0], r["source_id"][:2])
        if cc in MARKETS:
            by_cc[cc].append(r)
    res = {k: Counter() for k in CONFIGS}
    for cc, rs in by_cc.items():
        for name, eng in engines(cc, MarketReference.load(cc)).items():
            for r in rs:
                tl, tg = (float(x) for x in r["target_coordinate"].split(","))
                x = eng.validate(r["query"])
                ok = x.lat is not None and haversine(x.lat, x.lng, tl, tg) <= 100
                res[name]["n"] += 1
                res[name]["located_ok"] += ok and x.action in (ACCEPT, CONFIRM)
                res[name]["accept"] += x.action == ACCEPT
                res[name]["accept_ok"] += ok and x.action == ACCEPT
                res[name]["accept_bad"] += (x.action == ACCEPT and x.lat is not None
                                            and haversine(x.lat, x.lng, tl, tg) > 500)
    return {k: dict(v) for k, v in res.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", default=",".join(MARKETS))
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--jobs", type=int, default=3, help="每个进程加载一份 libpostal（约 2 GB）和一个市场的参考库")
    ap.add_argument("--postal-path", help="postal 绑定所在目录（没有装进 site-packages 时）")
    ap.add_argument("--responses", help="可选：真实流量包（0924 格式）")
    ap.add_argument("--split", default="dev", choices=["dev", "test"], help="test 只用来复核开发集上看到的提升")
    ap.add_argument("--tag", default="", help="输出文件名后缀（复核时用，不覆盖开发集的报告）")
    args = ap.parse_args()
    codes = [c for c in args.markets.split(",") if (ROOT / "data" / "markets" / c / "crf.model").exists()]
    with Pool(args.jobs, initializer=_init, initargs=(args.postal_path,)) as pool:
        markets = dict(pool.imap(evaluate_market, [(c, args.n, args.split) for c in codes]))
    traffic = None
    if args.responses:
        _init(args.postal_path)
        traffic = evaluate_traffic(args.responses)
    rep = {"split": args.split, "markets": markets, "traffic": traffic}
    (ROOT / "reports" / f"oss_parser_eval{args.tag}.json").write_text(
        json.dumps(rep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_md(rep, args.tag)


def write_md(rep: dict, tag: str = "") -> None:
    def ok(o):
        return o["正确·直接通过"] + o["正确·要求确认"]

    split = {"dev": "开发集", "test": "测试集"}[rep.get("split", "dev")]
    md = [f"# 开源解析器对比：libpostal vs 本方案（{split}）", "",
          "只换解析这一步，召回和验真用同一套参考库和判定规则。定位对 = 直接通过或请用户确认、且位置与标准答案一致"
          "（真实商户地址按距离，合成地址按道路 / 门牌）。", "",
          "| 市场 | 真实·本方案 | 真实·libpostal | 真实·本方案+libpostal 兜底 | 合成·本方案 | 合成·libpostal | 合成·兜底 | "
          "静默错误（真实，本方案 / libpostal / 兜底） |", "|---|---|---|---|---|---|---|---|"]
    tot = {k: {"real": Counter(), "synthetic": Counter()} for k in CONFIGS}
    for code, r in rep["markets"].items():
        cells = []
        for part in ("real", "synthetic"):
            for k in CONFIGS:
                cells.append(f"{100 * ok(r[k][part]['outcomes']):.1f}%")
                tot[k][part]["ok"] += ok(r[k][part]["outcomes"]) * r[k][part]["n"]
                tot[k][part]["silent"] += r[k][part]["outcomes"]["静默错误"] * r[k][part]["n"]
                tot[k][part]["n"] += r[k][part]["n"]
        silent = " / ".join(f"{100 * r[k]['real']['outcomes']['静默错误']:.1f}%" for k in CONFIGS)
        md.append(f"| {code} | " + " | ".join(cells) + f" | {silent} |")
    cells = [f"**{100 * tot[k][p]['ok'] / max(tot[k][p]['n'], 1):.1f}%**" for p in ("real", "synthetic") for k in CONFIGS]
    silent = " / ".join(f"{100 * tot[k]['real']['silent'] / max(tot[k]['real']['n'], 1):.1f}%" for k in CONFIGS)
    md.append("| **合计** | " + " | ".join(cells) + f" | {silent} |")
    if rep.get("traffic"):
        t = rep["traffic"]
        md += ["", "## 真实流量（0924 包里本方案 44 个市场的查询，不看 geo）", "",
               "| 解析 | 条数 | 定位对（≤ 100 米） | 直接通过 | 直接通过且对 | 直接通过但偏差 > 500 米 |", "|---|---|---|---|---|---|"]
        for k in CONFIGS:
            x = t[k]
            md.append(f"| {k} | {x['n']} | {x['located_ok']}（{100 * x['located_ok'] / x['n']:.1f}%） | {x['accept']} | "
                      f"{x['accept_ok']} | {x['accept_bad']} |")
    (ROOT / "reports" / f"oss_parser_eval{tag}.md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
