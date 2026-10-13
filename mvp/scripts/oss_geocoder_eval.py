"""开源地理编码器对比：整条链路（解析 + 召回 + 打分）与本方案比，用各市场开发集的真实商户地址。

  Addok   法国国家地址 API（api-adresse.data.gouv.fr）用的引擎（MIT），数据是法国国家地址库 BAN
          （巴黎 + 近郊 92 / 93 / 94 省）——"政府级地址库 + 开源检索"的实际做法
  Pelias  最常用的开源地理编码器（MIT：libpostal 解析 + Elasticsearch 检索打分），数据用本方案同一份参考库
          （澳洲官方地址表 G-NAF、路网、POI，带 suburb / 州），只比算法
比的是：给出的坐标离标准答案（商户坐标）≤ 250 米的比例，以及"直接通过"——开源引擎没有结论、只有分数，
按"准确率不低于本方案直接通过的准确率"取分数门槛，看能自动通过多少。

开源引擎各自装在单独的环境里，分几步：
  python scripts/oss_geocoder_eval.py export --market FR --out q_fr.jsonl [--n 600]
  <addok 的 python> scripts/oss_geocoder_eval.py addok --queries q_fr.jsonl --out addok_fr.jsonl  # 需 ADDOK_CONFIG_MODULE
  python scripts/oss_geocoder_eval.py pelias-data --market AU --out au.csv                           # Pelias csv-importer 的输入
  python scripts/oss_geocoder_eval.py pelias --queries q_au.jsonl --out pelias_au.jsonl [--url http://localhost:4000]
  python scripts/oss_geocoder_eval.py score --market FR --queries q_fr.jsonl --other addok_fr.jsonl --name Addok
输出：reports/oss_geocoder_eval.md、reports/oss_geocoder_eval.json（只有汇总数字）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OK_M = 250.0  # 与多市场评测的门牌级口径一致：商户坐标与地址点可能相隔一两百米


def export(args) -> None:
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "scripts"))
    from evaluate_markets import real_cases
    with open(args.out, "w", encoding="utf-8") as f:
        for i, c in enumerate(real_cases(args.market, args.n, "dev")):
            f.write(json.dumps({"i": i, "input": c["input"], "lat": c["lat"], "lng": c["lng"]}, ensure_ascii=False) + "\n")


def run_addok(args) -> None:
    from addok.config import config
    config.load()
    from addok.core import search
    with open(args.out, "w", encoding="utf-8") as f:
        for line in open(args.queries, encoding="utf-8"):
            q = json.loads(line)
            rs = search(q["input"], limit=1)
            r = rs[0] if rs else None
            f.write(json.dumps({"i": q["i"], "lat": float(r.lat) if r else None, "lng": float(r.lon) if r else None,
                                "score": float(r.score) if r else 0.0, "type": getattr(r, "type", "") if r else ""})
                    + "\n")


def pelias_data(args) -> None:
    """本方案的参考库 -> Pelias csv-importer 的 CSV：门址（同一门牌的多个单元只留一个点）、道路、POI，
    带上 suburb / 州 / 国家（parent_json），相当于 Pelias 用 Who's On First 补的行政区。"""
    import csv
    import sqlite3
    sys.path.insert(0, str(ROOT))
    from avmvp.intl.reference import MarketReference
    ref = MarketReference.load(args.market)
    state = {"2": ("New South Wales", "NSW"), "3": ("Victoria", "VIC")}  # 试点是悉尼、墨尔本
    db = sqlite3.connect(ref.dir / "reference.sqlite")

    def parent(locality: str, pc: str) -> str:
        p = {"country": [{"name": "Australia", "abbr": "AUS", "id": "AU", "source": "custom"}]}
        if locality:
            p["locality"] = [{"name": locality.title(), "id": locality.lower(), "source": "custom"}]
        if pc and pc[:1] in state:
            p["region"] = [{"name": state[pc[:1]][0], "abbr": state[pc[:1]][1], "id": pc[:1], "source": "custom"}]
        return json.dumps(p, ensure_ascii=False)
    cols = ["id", "source", "layer", "name", "housenumber", "street", "postcode", "lat", "lon", "parent_json"]
    seen = set()
    n = 0
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for rid, num, street, pc, loc, lat, lng in db.execute(
                "SELECT id, number, street_name, postcode, locality, lat, lng FROM addr"):
            k = (street, num, pc)
            if not num or not street or k in seen:
                continue
            seen.add(k)
            w.writerow([f"a{rid}", "ref", "address", f"{num} {street}", num, street, pc or "", lat, lng,
                        parent(loc or "", pc or "")])
            n += 1
        for s_ in ref.streets:
            loc = next((ref.areas[a].name for a in s_.areas if ref.areas[a].subtype in ("macrohood", "locality")), "")
            w.writerow([f"s{s_.id}", "ref", "street", s_.name, "", s_.name, "", s_.lat, s_.lng, parent(loc, "")])
            n += 1
        for pid, name, lat, lng, pc in db.execute("SELECT id, name, lat, lng, postcode FROM poi"):
            if name:
                w.writerow([f"p{pid}", "ref", "venue", name, "", "", pc or "", lat, lng, parent("", pc or "")])
                n += 1
    print(n, "rows")


def run_pelias(args) -> None:
    import urllib.parse
    import urllib.request
    with open(args.out, "w", encoding="utf-8") as f:
        for line in open(args.queries, encoding="utf-8"):
            q = json.loads(line)
            url = f"{args.url}/v1/search?" + urllib.parse.urlencode({"text": q["input"], "size": 1})
            feats = json.loads(urllib.request.urlopen(url, timeout=30).read()).get("features") or []
            g = feats[0] if feats else None
            lng, lat = g["geometry"]["coordinates"] if g else (None, None)
            props = g["properties"] if g else {}
            f.write(json.dumps({"i": q["i"], "lat": lat, "lng": lng, "score": props.get("confidence", 0.0),
                                "type": props.get("layer", "")}) + "\n")


def score(args) -> None:
    sys.path.insert(0, str(ROOT))
    from avmvp.intl.engine import ACCEPT, CONFIRM, Engine
    from avmvp.intl.reference import haversine
    qs = [json.loads(x) for x in open(args.queries, encoding="utf-8")]
    other = {r["i"]: r for r in map(json.loads, open(args.other, encoding="utf-8"))}
    eng = Engine(args.market, "hybrid")
    ours, oss = [], []
    for q in qs:
        res = eng.validate(q["input"])
        d = haversine(res.lat, res.lng, q["lat"], q["lng"]) if res.lat is not None else None
        ours.append({"ok": d is not None and d <= OK_M, "far": d is not None and d > 1000, "action": res.action})
        a = other.get(q["i"]) or {}
        d = haversine(a["lat"], a["lng"], q["lat"], q["lng"]) if a.get("lat") is not None else None
        oss.append({"ok": d is not None and d <= OK_M, "far": d is not None and d > 1000,
                    "score": a.get("score") or 0.0, "type": a.get("type", "")})
    acc = [o for o in ours if o["action"] == ACCEPT]
    acc_prec = sum(o["ok"] for o in acc) / max(len(acc), 1)
    # 开源引擎按分数门槛自动通过（分数 ≥ 门槛的全部通过，同分的一起进出）：准确率不低于本方案"直接通过"的
    # 准确率时，最多能通过多少
    ranked = sorted(oss, key=lambda a: -a["score"])
    best_k = 0
    for t in sorted({a["score"] for a in oss if a["score"] > 0}, reverse=True):
        sel = [a for a in oss if a["score"] >= t]
        if sum(a["ok"] for a in sel) / len(sel) >= acc_prec:
            best_k = len(sel)
    entry = {
        "market": args.market, "n": len(qs), "ok_m": OK_M,
        "ours": {"located_ok": sum(o["ok"] for o in ours),
                 "located_ok_not_fix": sum(o["ok"] and o["action"] in (ACCEPT, CONFIRM) for o in ours),
                 "far": sum(o["far"] for o in ours), "accept": len(acc), "accept_ok": sum(o["ok"] for o in acc),
                 "accept_far": sum(o["far"] for o in acc)},
        "other": {"located_ok": sum(a["ok"] for a in oss), "far": sum(a["far"] for a in oss),
                  "top_score": sum(a["score"] >= max(a_["score"] for a_ in oss) for a in oss),
                  "top_score_ok": sum(a["ok"] and a["score"] >= max(a_["score"] for a_ in oss) for a in oss),
                  "premise": sum(a["type"] in ("housenumber", "address") for a in oss),
                  "auto_at_same_precision": best_k, "auto_ok": sum(a["ok"] for a in ranked[:best_k]),
                  "auto_far": sum(a["far"] for a in ranked[:best_k])},
    }
    path = ROOT / "reports" / "oss_geocoder_eval.json"
    rep = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    rep = rep if "runs" in rep else {"runs": {}}
    rep["runs"][f"{args.name}|{args.market}"] = entry
    path.write_text(json.dumps(rep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_md(rep)


DATA_NOTE = {"Addok": "法国国家地址库 BAN（巴黎 + 92 / 93 / 94 省）；本方案用自己的参考库",
             "Pelias": "与本方案同一份参考库（G-NAF 门址、路网、POI，带 suburb / 州）；Pelias 没有本方案从商户地址推出的门牌点"}


def write_md(rep: dict) -> None:
    md = ["# 开源地理编码器对比（各市场开发集真实商户地址）", "",
          f"定位对 = 给出的坐标离商户坐标 ≤ {OK_M:.0f} 米。开源引擎只有分数、没有结论，按\"准确率不低于本方案直接通过的准确率\""
          "取分数门槛，看能自动通过多少。", "",
          "| 对比 | 市场 | 条数 | 数据 | 系统 | 定位对（Top1） | 偏差 > 1 公里 | 自动通过 | 自动通过里定位对 | 自动通过里偏差 > 1 公里 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for key_, e in rep["runs"].items():
        name, market = key_.split("|")
        n, o, a = e["n"], e["ours"], e["other"]

        def pct(x):
            return f"{100 * x / n:.1f}%"
        md.append(f"| {name} | {market} | {n} | {DATA_NOTE.get(name, '')} | 本方案 | {o['located_ok']}（{pct(o['located_ok'])}） | "
                  f"{o['far']}（{pct(o['far'])}） | {o['accept']}（{pct(o['accept'])}） | "
                  f"{100 * o['accept_ok'] / max(o['accept'], 1):.1f}% | {o['accept_far']} |")
        md.append(f"| | | | | {name} | {a['located_ok']}（{pct(a['located_ok'])}） | {a['far']}（{pct(a['far'])}） | "
                  f"{a['auto_at_same_precision']}（{pct(a['auto_at_same_precision'])}） | "
                  f"{100 * a['auto_ok'] / max(a['auto_at_same_precision'], 1):.1f}% | {a['auto_far']} |")
    md.append("")
    for key_, e in rep["runs"].items():
        a = e["other"]
        if "top_score" in a:
            md.append(f"- {key_.split('|')[0]}：分数最高（同分）的 {a['top_score']} 条里定位对 {a['top_score_ok']} 条"
                      f"（{100 * a['top_score_ok'] / max(a['top_score'], 1):.1f}%）——分数门槛最严时的准确率。")
    (ROOT / "reports" / "oss_geocoder_eval.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--out", required=True)
    e.add_argument("--market", default="FR")
    e.add_argument("--n", type=int, default=600)
    r = sub.add_parser("addok")
    r.add_argument("--queries", required=True)
    r.add_argument("--out", required=True)
    s = sub.add_parser("score")
    s.add_argument("--queries", required=True)
    s.add_argument("--other", required=True, help="开源引擎的结果（addok / pelias 子命令的输出）")
    s.add_argument("--name", required=True, help="Addok / Pelias")
    s.add_argument("--market", default="FR")
    d = sub.add_parser("pelias-data")
    d.add_argument("--market", default="AU")
    d.add_argument("--out", required=True)
    p = sub.add_parser("pelias")
    p.add_argument("--queries", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--url", default="http://localhost:4000")
    args = ap.parse_args()
    {"export": export, "addok": run_addok, "score": score, "pelias-data": pelias_data,
     "pelias": run_pelias}[args.cmd](args)


if __name__ == "__main__":
    main()
