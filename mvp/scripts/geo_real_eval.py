"""geo 服务真实返回的评测：每条有用户输入、geo 的 Top1 门址和坐标、库内目标门址坐标（标准答案）。

标准答案按距离：geo（或最终结论）的坐标离目标 ≤ 100 米算对，> 500 米算错，中间算"同街附近"。
比较两种用法：
  直接用 geo   geo 有结果就采用
  geo + 核对层 本方案的市场（44 个）走 validate_with_geo（参考库 + 本引擎；试点城市以外走范围守卫）；
              其余国家走 geo_free.validate_free（只用原文 + 全国地名表）
关心的数字：直接通过（ACCEPT）里错的有多少（静默错误）、geo 错的被拦下多少、geo 对的放行多少。

  python scripts/geo_real_eval.py --responses final_effective_full_responses_851.jsonl [--details 明细.jsonl]
输出：reports/geo_real_eval.md、reports/geo_real_eval.json（只有汇总数字，不含原文）
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp.intl.engine import ACCEPT, CONFIRM, Engine  # noqa: E402
from avmvp.intl.geo_check import parse_geo, validate_with_geo  # noqa: E402
from avmvp.intl.geo_free import validate_free  # noqa: E402
from avmvp.intl.markets import MARKETS  # noqa: E402
from avmvp.intl.reference import haversine  # noqa: E402

ISO3 = {"KSA": "SA", "UAE": "AE", "AUS": "AU", "AUT": "AT", "BEL": "BE", "BHR": "BH", "BRA": "BR", "COL": "CO",
        "DEU": "DE", "DOM": "DO", "EGY": "EG", "ESP": "ES", "FRA": "FR", "GBR": "GB", "IDN": "ID", "ITA": "IT",
        "KAZ": "KZ", "KWT": "KW", "MEX": "MX", "MYS": "MY", "NLD": "NL", "NZL": "NZ", "OMN": "OM", "PER": "PE",
        "PHL": "PH", "POL": "PL", "PRT": "PT", "QAT": "QA", "SGP": "SG", "THA": "TH", "TUR": "TR", "UZB": "UZ",
        "VNM": "VN", "ZAF": "ZA", "SAU": "SA", "ARE": "AE"}
OK_M, BAD_M = 100.0, 500.0


def label(lat, lng, truth) -> str:
    if lat is None:
        return "none"
    d = haversine(lat, lng, truth[0], truth[1])
    return "ok" if d <= OK_M else "bad" if d > BAD_M else "near"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", required=True)
    ap.add_argument("--details")
    args = ap.parse_args()
    rows = [json.loads(x) for x in open(args.responses, encoding="utf-8")]
    engines: dict[str, Engine] = {}
    out = []
    for r in rows:
        cc = ISO3.get(r["source_id"].split(":")[0], r["source_id"][:2])
        tl, tg = (float(x) for x in r["target_coordinate"].split(","))
        geos = parse_geo(r.get("response_body") or "")
        g = geos[0] if geos else None
        if cc in MARKETS:
            eng = engines.get(cc) or engines.setdefault(cc, Engine(cc, "hybrid"))
            res = validate_with_geo(eng, r["query"], r.get("response_body") or "")
            mode = "outside" if res.coverage is not None and res.coverage.status == "OUTSIDE" else "reference"
        else:
            res = validate_free(cc, r["query"], r.get("response_body") or "")
            mode = "no_reference"
        out.append({"case": r["case_id"], "cc": cc, "mode": mode, "noise": r.get("noise_severity", ""),
                    "geo": label(g.lat, g.lng, (tl, tg)) if g else "empty",
                    "action": res.action, "final": label(res.lat, res.lng, (tl, tg)),
                    "reasons": list(res.reasons)[:6], "query": r["query"],
                    "geo_addr": g.formatted if g else "", "geo_num": g.number if g else "",
                    "geo_route": g.route if g else "", "target": r.get("target_address", "")})
        print(len(out), cc, out[-1]["geo"], res.action, out[-1]["final"], flush=True) if len(out) % 50 == 0 else None
    if args.details:
        with open(args.details, "w", encoding="utf-8") as f:
            for o in out:
                f.write(json.dumps(o, ensure_ascii=False) + "\n")

    def summary(xs: list[dict]) -> dict:
        n = len(xs)
        c = Counter((x["geo"], x["action"], x["final"]) for x in xs)
        geo_ok = sum(x["geo"] == "ok" for x in xs)
        geo_bad = sum(x["geo"] == "bad" for x in xs)
        acc = [x for x in xs if x["action"] == ACCEPT]
        return {"n": n, "geo_empty": sum(x["geo"] == "empty" for x in xs), "geo_ok": geo_ok,
                "geo_near": sum(x["geo"] == "near" for x in xs), "geo_bad": geo_bad,
                "accept": len(acc), "accept_ok": sum(x["final"] == "ok" for x in acc),
                "accept_near": sum(x["final"] == "near" for x in acc),
                "accept_bad": sum(x["final"] == "bad" for x in acc),
                "confirm": sum(x["action"] == CONFIRM for x in xs),
                "confirm_ok": sum(x["action"] == CONFIRM and x["final"] == "ok" for x in xs),
                "fix": sum(x["action"] not in (ACCEPT, CONFIRM) for x in xs),
                "geo_bad_caught": sum(x["geo"] == "bad" and not (x["action"] == ACCEPT and x["final"] == "bad")
                                      for x in xs),
                "geo_ok_accepted": sum(x["geo"] == "ok" and x["action"] == ACCEPT for x in xs),
                "detail": {f"{a}|{b}|{d}": v for (a, b, d), v in c.items()}}

    groups = defaultdict(list)
    for o in out:
        groups["全部"].append(o)
        groups[{"reference": "本方案市场·试点城市内", "outside": "本方案市场·试点城市外",
                "no_reference": "没有参考库的国家"}[o["mode"]]].append(o)
        groups[f"噪声:{o['noise']}"].append(o)
    by_cc = defaultdict(list)
    for o in out:
        by_cc[o["cc"]].append(o)
    rep = {"groups": {k: summary(v) for k, v in groups.items()}, "countries": {k: summary(v) for k, v in by_cc.items()}}
    json.dump(rep, open(ROOT / "reports" / "geo_real_eval.json", "w"), ensure_ascii=False, indent=1)

    def pct(a, b):
        return f"{100 * a / b:.1f}%" if b else "—"
    md = ["# geo 服务真实返回评测（核对层）", "",
          f"数据：{len(out)} 条线上查询，每条有 geo 的 Top1 门址与坐标、库内目标门址坐标（标准答案）。"
          f"geo 坐标离目标 ≤ {OK_M:.0f} 米算对，> {BAD_M:.0f} 米算错，中间算同街附近。", "",
          "**直接用 geo**：geo 有结果就采用。**geo + 核对层**：直接通过（ACCEPT）的才自动采用，其余请用户确认（CONFIRM）或补全（FIX）。", "",
          "| 分组 | 条数 | geo 对 | geo 附近 | geo 错 | geo 空 | 直接用 geo：错的被采用 | 核对层直接通过 | 其中对 | 其中错（静默错误） | geo 错被拦下 | geo 对被放行 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, s in rep["groups"].items():
        md.append(f"| {k} | {s['n']} | {pct(s['geo_ok'], s['n'])} | {pct(s['geo_near'], s['n'])} | {pct(s['geo_bad'], s['n'])} | "
                  f"{pct(s['geo_empty'], s['n'])} | {s['geo_bad']}（{pct(s['geo_bad'], s['n'])}） | {s['accept']}（{pct(s['accept'], s['n'])}） | "
                  f"{pct(s['accept_ok'], s['accept'])} | {s['accept_bad']}（{pct(s['accept_bad'], s['accept'])}） | "
                  f"{pct(s['geo_bad_caught'], s['geo_bad'])} | {pct(s['geo_ok_accepted'], s['geo_ok'])} |")
    md += ["", "## 各国", "", "| 国家 | 条数 | geo 对 | geo 错 | geo 空 | 直接通过 | 其中错 | geo 错被拦下 | geo 对被放行 |",
           "|---|---|---|---|---|---|---|---|---|"]
    for k, s in sorted(rep["countries"].items(), key=lambda kv: -kv[1]["n"]):
        md.append(f"| {k} | {s['n']} | {pct(s['geo_ok'], s['n'])} | {pct(s['geo_bad'], s['n'])} | {pct(s['geo_empty'], s['n'])} | "
                  f"{s['accept']} | {s['accept_bad']} | {pct(s['geo_bad_caught'], s['geo_bad'])} | {pct(s['geo_ok_accepted'], s['geo_ok'])} |")
    (ROOT / "reports" / "geo_real_eval.md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
