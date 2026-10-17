"""用客户门址底表合成"用户写法"的查询，评测引擎在客户真实门址分布上的表现（合成数据，不是真实用户输入）。

底表每行一条标准门址 + 坐标，但没有 suburb / 邮编；先用 base_table_health.py 的补齐结果（--enrich-out）补上，
只取与 G-NAF 吻合（30 米内）的门址。每条门址按一种写法渲染：
  full          5/10-12 Smith St, Bondi NSW 2026（单元写法、路类型缩写随机）
  no_postcode   …, Bondi Beach NSW
  postcode_only … NSW 2026（不写 suburb）
  line_only     只有门址行（和底表、GU 索引里的文字一样，没有 suburb / 邮编，可能有同名）
  typo_street   路名错一个字母
  typo_suburb   suburb 错一个字母
  messy         小写、不加逗号、前后带电话和收件人
判对错看坐标：门牌级 50 米内（门牌附近 150 米），道路级道路经过 150 米内；只到片区记"只到片区"。
大型小区里单元的坐标常与门牌点相隔一两百米，所以给出的路名和门牌与底表一致、相距 1 公里内也算门牌对。
按编号哈希固定分开发 / 测试两半，开发集用来改进，测试集只在最后跑。

  python scripts/base_table_synth_eval.py 底表.csv.xz 补齐结果.csv.gz --split dev --n 2000 [--tag _v1]
输出：reports/base_synth_eval<tag>.md / .json（只有汇总）；--examples-out 另把错例（由底表门址渲染的输入）写到
仓库以外的文件，只用于本地排查
"""

from __future__ import annotations

import argparse
import collections
import csv
import gzip
import hashlib
import json
import lzma
import random
import re
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp.intl.engine import ACCEPT, ADD_SUB, Engine, dist_to_street  # noqa: E402
from avmvp.intl.markets import MARKETS  # noqa: E402
from avmvp.intl.national import number_variants  # noqa: E402
from avmvp.intl.reference import MarketReference, haversine, number_key  # noqa: E402
from avmvp.intl.text import key  # noqa: E402
from base_table_health import ADDR, FLAT, unsuffixed  # noqa: E402

VARIANTS = ["full", "no_postcode", "postcode_only", "line_only", "typo_street", "typo_suburb", "messy"]
OUTCOMES = ["门牌对·直接通过", "门牌对·要确认", "道路对", "只到片区 / 判 FIX", "错误建议", "静默错误"]
SHORT = {"STREET": "St", "ROAD": "Rd", "AVENUE": "Ave", "PLACE": "Pl", "CRESCENT": "Cres", "DRIVE": "Dr",
         "PARADE": "Pde", "CLOSE": "Cl", "CIRCUIT": "Cct", "COURT": "Ct", "HIGHWAY": "Hwy", "LANE": "Ln",
         "BOULEVARD": "Blvd", "TERRACE": "Tce", "GROVE": "Gr", "ESPLANADE": "Esp", "PARKWAY": "Pkwy"}
LONG = {v.upper(): k for k, v in SHORT.items()} | {"AVE": "AVENUE", "CRES": "CRESCENT", "PDE": "PARADE",
                                                 "CLOS": "CLOSE", "CCT": "CIRCUIT", "HWY": "HIGHWAY", "LN": "LANE"}
FLAT_WORD = re.compile(rf"^{FLAT}\b")


def opener(path):
    return lzma.open if path.endswith(".xz") else gzip.open if path.endswith(".gz") else open


def half(vec_id: str) -> str:
    return "dev" if int(hashlib.md5(vec_id.encode()).hexdigest()[0], 16) < 8 else "test"


def title(s: str) -> str:
    return " ".join(w if any(c.isdigit() for c in w) else w.capitalize() for w in s.split())


def typo(word: str, rnd: random.Random) -> str:
    i = rnd.randrange(1, len(word) - 1)
    op = rnd.choice(("swap", "drop", "double", "sub"))
    if op == "swap":
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    if op == "drop":
        return word[:i] + word[i + 1:]
    if op == "double":
        return word[:i] + word[i] + word[i:]
    return word[:i] + rnd.choice("aeiou" if word[i] not in "aeiou" else "rstnl") + word[i + 1:]


def render(row: dict, variant: str, rnd: random.Random) -> str | None:
    up = re.sub(r"\s+", " ", row["address"].upper()).strip()
    m = ADDR.match(up)
    if not m:
        return None
    unit, _level, unit2, num, num2, street = m.groups()
    unit = unit or unit2
    words = street.split()
    t = LONG.get(words[-1], words[-1])
    words[-1] = SHORT.get(t, t.capitalize()).upper() if rnd.random() < 0.5 else t  # 路类型一半写缩写
    street_t = title(" ".join(words))
    number = f"{num}-{num2}" if num2 else num
    suburb, pc = title(row["suburb"]), row["postcode"]
    if variant == "typo_street":
        longest = max(range(len(words) - 1 or 1), key=lambda i: len(words[i]))
        if len(words[longest]) < 5:
            return None
        sw = street_t.split()
        sw[longest] = typo(sw[longest], rnd)
        street_t = " ".join(sw)
    if variant == "typo_suburb":
        sw = suburb.split()
        j = max(range(len(sw)), key=lambda i: len(sw[i]))
        if len(sw[j]) < 5:
            return None
        sw[j] = typo(sw[j], rnd)
        suburb = " ".join(sw)
    if unit:
        flat_word = FLAT_WORD.match(up)
        kind = flat_word.group(0) if flat_word else "UNIT"
        if kind == "UNIT":
            line = rnd.choice((f"{unit}/{number} {street_t}", f"Unit {unit}, {number} {street_t}",
                               f"U{unit}/{number} {street_t}", f"Apt {unit} {number} {street_t}"))
        else:
            line = f"{kind.capitalize()} {unit}, {number} {street_t}"
    else:
        line = f"{number} {street_t}"
    if variant in ("full", "typo_street", "typo_suburb"):
        return f"{line}, {suburb} NSW {pc}"
    if variant == "no_postcode":
        return f"{line}, {suburb} NSW"
    if variant == "postcode_only":
        return f"{line} NSW {pc}"
    if variant == "line_only":
        return line
    phone = f"04{rnd.randrange(10, 99)} {rnd.randrange(100, 999)} {rnd.randrange(100, 999)}"
    who = rnd.choice(("attn: j. smith", "c/o reception", "leave at door", "deliver to mia"))
    return f"{who} {line} {suburb} nsw {pc} ph {phone}".lower().replace(",", "")


def cases(table: str, enrich: str, split: str, n: int, seed: int = 17) -> list[dict]:
    """开发 / 测试半边里与 G-NAF 吻合的门址，蓄水池抽 n 条，轮流分配写法。"""
    rnd = random.Random(seed)
    pool: list[dict] = []
    seen = 0
    with opener(table)(table, "rt", encoding="utf-8", newline="") as ft, \
            opener(enrich)(enrich, "rt", encoding="utf-8", newline="") as fe:
        for row, e in zip(csv.DictReader(ft), csv.DictReader(fe)):
            assert row["vec_id"] == e["id"], "补齐结果要和底表同序"
            if e["class"] != "match_30m" or not e["suburb"] or half(row["vec_id"]) != split:
                continue
            row = {"vec_id": row["vec_id"], "address": row["address"], "suburb": e["suburb"], "postcode": e["postcode"],
                   "lat": float(row["y"]), "lng": float(row["x"])}
            seen += 1
            if len(pool) < n:
                pool.append(row)
            else:
                j = rnd.randrange(seen)
                if j < n:
                    pool[j] = row
    out = []
    for i, row in enumerate(pool):
        v = VARIANTS[i % len(VARIANTS)]
        text = render(row, v, rnd)
        if text is None:
            v, text = "full", render(row, "full", rnd)
        if text:
            out.append({**row, "variant": v, "input": text})
    return out


def in_pilot(lat, lng) -> bool:
    return any(x0 <= lng <= x1 and y0 <= lat <= y1 for _, (x0, y0, x1, y1) in MARKETS["AU"].regions)


def same_address(res, c) -> bool:
    """给出的路名 + 门牌与底表这条门址相同（方位后缀不计；区间门牌给出首号或尾号也算）。"""
    m = ADDR.match(re.sub(r"\s+", " ", c["address"].upper()).strip())
    route = (res.components.get("route") or {}).get("text") or ""
    num = (res.components.get("street_number") or {}).get("text") or ""
    if not m or not route or not num:
        return False
    want = number_key(f"{m.group(4)}-{m.group(5)}" if m.group(5) else m.group(4))
    return unsuffixed(key(route.upper(), "AU")) == unsuffixed(key(m.group(6), "AU")) \
        and number_key(num) in number_variants(want)  # 7-9 写的楼，给出 7 也算同一处


def judge(eng: Engine, res, c) -> tuple[str, float | None]:
    if res.lat is None or res.granularity in ("LOCALITY", "OTHER"):
        return ("只到片区 / 判 FIX" if res.action != ACCEPT else "静默错误"), None
    d = haversine(res.lat, res.lng, c["lat"], c["lng"])
    direct = res.action in (ACCEPT, ADD_SUB)
    if res.granularity in ("PREMISE", "PREMISE_PROXIMITY"):
        if d <= (50 if res.granularity == "PREMISE" else 150) or (d <= 1000 and same_address(res, c)):
            return ("门牌对·直接通过" if direct else "门牌对·要确认"), d
    elif res.granularity == "ROUTE":
        b = res.best
        dd = dist_to_street(eng.ref, b.street, c["lat"], c["lng"]) if b is not None and b.street is not None else d
        if dd <= 150:
            return "道路对", d
    return ("静默错误" if direct else "错误建议"), d


def evaluate(eng: Engine, cs: list[dict]) -> dict:
    groups = collections.defaultdict(list)
    t = time.perf_counter()
    for c in cs:
        res = eng.validate(c["input"])
        o, d = judge(eng, res, c)
        rec = (o, d, res.action, res.granularity)
        groups["all"].append(rec); groups[c["variant"]].append(rec)
        groups["in_pilot" if in_pilot(c["lat"], c["lng"]) else "outside_pilot"].append(rec)
        if o in ("静默错误", "错误建议") and len(groups.setdefault("_ex_" + o, [])) < 12:
            groups["_ex_" + o].append((c["variant"], c["input"], res.action, res.granularity,
                                       None if d is None else round(d)))
    ms = (time.perf_counter() - t) * 1000 / max(len(cs), 1)
    out = {}
    for k, recs in groups.items():
        if k.startswith("_ex_"):
            out[k] = recs
            continue
        n = len(recs); oc = collections.Counter(r[0] for r in recs)
        ds = [r[1] for r in recs if r[1] is not None and r[0].startswith("门牌对")]
        out[k] = {"n": n, "outcomes": {o: oc[o] / n for o in OUTCOMES},
                  "located": (oc["门牌对·直接通过"] + oc["门牌对·要确认"] + oc["道路对"]) / n,
                  "premise": (oc["门牌对·直接通过"] + oc["门牌对·要确认"]) / n,
                  "median_premise_err_m": round(statistics.median(ds), 1) if ds else None}
    out["ms"] = ms
    return out


def write_report(res: dict, args) -> None:
    lines = [f"# 悉尼底表合成查询评测（{args.split}，{res['all']['n']} 条，解析器 {args.parser}）", "",
             "> 合成数据：输入按用户常见写法从客户门址底表渲染（suburb / 邮编由 G-NAF 补齐），不是真实用户输入。",
             "> 判对错看坐标：门牌级 50 米内（门牌附近 150 米；路名门牌与底表相同时 1 公里内），道路级道路经过 150 米内。", "",
             "| 写法 | 条数 | 定位对 | 门牌对 | 门牌对·直接通过 | 门牌对·要确认 | 道路对 | 只到片区 / 判 FIX | 错误建议 | 静默错误 |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for k in ["all", *VARIANTS, "in_pilot", "outside_pilot"]:
        r = res.get(k)
        if not r:
            continue
        o = r["outcomes"]
        lines.append(f"| {k} | {r['n']} | {100 * r['located']:.1f}% | {100 * r['premise']:.1f}% | "
                     + " | ".join(f"{100 * o[x]:.1f}%" for x in OUTCOMES) + " |")
    lines += ["", f"平均 {res['ms']:.1f} ms/条。", ""]
    (ROOT / "reports" / f"base_synth_eval{args.tag}.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("table")
    ap.add_argument("enrich")
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("--n", type=int, default=2100)
    ap.add_argument("--parser", default="hybrid")
    ap.add_argument("--tag", default="")
    ap.add_argument("--examples-out", default="", help="错例写到这里（仓库以外，含由底表门址渲染的输入）")
    args = ap.parse_args()
    cs = cases(args.table, args.enrich, args.split, args.n)
    eng = Engine("AU", args.parser, MarketReference.load("AU"))
    res = evaluate(eng, cs)
    examples = {k: res.pop(k) for k in [k for k in res if k.startswith("_ex_")]}
    if args.examples_out:
        Path(args.examples_out).write_text(json.dumps(examples, ensure_ascii=False, indent=1))
    (ROOT / "reports" / f"base_synth_eval{args.tag}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    write_report(res, args)
    for k in ["all", *VARIANTS, "in_pilot", "outside_pilot"]:
        r = res.get(k)
        if r:
            print(f"{k:14} n={r['n']:5} 定位对 {100 * r['located']:5.1f}% 门牌对 {100 * r['premise']:5.1f}% "
                  f"直接通过且对 {100 * r['outcomes']['门牌对·直接通过']:5.1f}% 静默 {100 * r['outcomes']['静默错误']:4.1f}%")


if __name__ == "__main__":
    main()
