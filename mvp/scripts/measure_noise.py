"""从真实人写的新加坡地址里统计"噪声"的种类和比例，作为构造测试集的依据。

数据（Overture Maps 2026-09-23.1，按新加坡范围下载到 data/overture/，见 scripts/fetch_overture.py）：
  - 官方地址表：addresses 主题（来源 OpenAddresses sg/countrywide，2026-09 更新），当作"标准答案"
  - 商户地址：places 主题里商户自己填写的地址（主要来自 Meta 商户主页，另有 Foursquare、Microsoft 等）

做法：对每条带邮编的商户地址，取官方地址表里同一邮编的地址作为标准写法，逐项比对：
  邮编是否缺失 / 与门牌道路矛盾，门牌号是否缺失 / 不同，道路是否全称 / 缩写 / 拼错 / 没写，
  是否带单元号及其写法，是否带 Blk 前缀、楼宇名、"Singapore"、重复片段，大小写风格 ……

注意：商户主页上的地址不等于客户下单时填的地址（一部分由平台自动格式化，缩写风格偏统一），
比例用于给出"量级"和"噪声种类清单"，与文献数据一起确定测试集的注入比例（见 docs/11）。

  python scripts/measure_noise.py        # 输出 reports/noise_stats.md 与 reports/noise_stats.json
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "overture"

# 比对用的缩写展开表（独立实现；只用于统计，不影响校验器）
EXPAND = {
    "AVE": "AVENUE", "AV": "AVENUE", "RD": "ROAD", "ST": "STREET", "DR": "DRIVE", "CRES": "CRESCENT",
    "CL": "CLOSE", "LN": "LANE", "BLVD": "BOULEVARD", "CTRL": "CENTRAL", "CTL": "CENTRAL", "NTH": "NORTH",
    "STH": "SOUTH", "JLN": "JALAN", "JL": "JALAN", "LOR": "LORONG", "LRG": "LORONG", "BT": "BUKIT", "BKT": "BUKIT",
    "UPP": "UPPER", "UPR": "UPPER", "TG": "TANJONG", "KG": "KAMPONG", "TER": "TERRACE", "TERR": "TERRACE",
    "PL": "PLACE", "PK": "PARK", "HTS": "HEIGHTS", "GDNS": "GARDENS", "GDN": "GARDEN", "IND": "INDUSTRIAL",
    "MT": "MOUNT", "VW": "VIEW", "GR": "GROVE", "GRV": "GROVE", "CIR": "CIRCLE", "SQ": "SQUARE", "WK": "WALK",
    "HWY": "HIGHWAY", "EXPY": "EXPRESSWAY", "CTR": "CENTRE", "E": "EAST", "W": "WEST", "N": "NORTH", "S": "SOUTH",
    # 地图平台格式化器常用的缩写（抽检发现，不是错拼）
    "PRK": "PARK", "WY": "WAY", "HL": "HILL", "GRN": "GREEN", "LP": "LOOP", "FLD": "FIELD", "CT": "COURT",
    "CCT": "CIRCUIT", "TCE": "TERRACE", "PDE": "PARADE", "PROM": "PROMENADE", "WLK": "WALK", "LK": "LINK",
    "RS": "RISE", "CRSS": "CROSS", "CLS": "CLOSE", "VIS": "VISTA", "BR": "BRIDGE", "PT": "POINT", "DRV": "DRIVE",
}
UNIT_RE = re.compile(r"#\s*[A-Z]?\d{1,3}[A-Z]?\s*-\s*[A-Z]?\d{1,4}[A-Z]?|\b(?:LEVEL|LVL|FLOOR|FLR)\s*\d{1,3}\b|\bUNIT\s+\S+",
                     re.I)
UNIT_FORMS = [
    ("#01-23", re.compile(r"#[A-Z]?\d{2}-[A-Z]?\d{1,4}[A-Z]?\b", re.I)),
    ("# 01-23 / #01 - 23（有空格）", re.compile(r"#\s+\S|#\S+\s+-\s*\S|#\S+-\s+\S", re.I)),
    ("#1-23（楼层不补 0）", re.compile(r"#[1-9]-\d", re.I)),
    ("Level / Lvl / Floor", re.compile(r"\b(?:LEVEL|LVL|FLOOR|FLR)\s*\d", re.I)),
    ("Unit …", re.compile(r"\bUNIT\s+\S", re.I)),
]


def norm(s: str) -> str:
    s = s.upper().replace("\\N", " ")
    s = re.sub(r"[’'`]", "", s)
    s = re.sub(r"[^A-Z0-9#@&\- ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def expand(s: str) -> str:
    return " ".join(EXPAND.get(t, t) for t in s.split())


def case_style(s: str) -> str:
    letters = [c for c in s if c.isalpha() and c.isascii()]
    if not letters:
        return "无字母"
    if all(c.isupper() for c in letters):
        return "全大写"
    if all(c.islower() for c in letters):
        return "全小写"
    return "首字母大写 / 混合"


def load_official():
    rows = pq.read_table(DATA / "sg_address.parquet", columns=["street", "number", "unit", "postcode"]).to_pylist()
    by_postal: dict[str, list[tuple[str, str, list[str]]]] = defaultdict(list)
    by_num_street: dict[tuple[str, str], set[str]] = defaultdict(set)
    agg: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for r in rows:
        num, street, pc = str(r["number"] or "").upper(), (r["street"] or "").upper(), r["postcode"] or ""
        if r["unit"] and r["unit"] != "NIL":
            agg[(num, street, pc)].add(r["unit"].upper())
        else:
            agg[(num, street, pc)]
    for (num, street, pc), blds in agg.items():
        by_postal[pc].append((num, street, sorted(blds)))
        by_num_street[(num, norm(street))].add(pc)
    return by_postal, by_num_street


def street_match(text_n: str, text_x: str, street: str) -> tuple[str, int | None]:
    """商户地址里道路的写法（全称 / 缩写 / 拼错 / 没写），以及道路在展开后文字里的起始词位置。"""
    s_n = norm(street)
    toks, k = text_x.split(), len(s_n.split())
    for form, text in (("全称", text_n), ("缩写", text_x)):
        m = re.search(rf"(?<![A-Z0-9]){re.escape(s_n)}(?![A-Z0-9])", text)
        if m:
            return form, len(text_x[: _pos_in_x(text, text_x, m.start())].split())
    best, pos = 0.0, None
    for size in {max(k - 1, 1), k, k + 1}:
        for i in range(0, max(len(toks) - size + 1, 1)):
            sc = fuzz.ratio(" ".join(toks[i:i + size]), s_n)
            if sc > best:
                best, pos = sc, i
    return ("拼错（可认出）", pos) if best >= 85 else ("没写 / 认不出", None)


def _pos_in_x(text: str, text_x: str, start: int) -> int:
    """把 text 里的字符位置换算成 text_x 里的字符位置（两者按词一一对应）。"""
    n_words = len(text[:start].split())
    return len(" ".join(text_x.split()[:n_words])) + (1 if n_words else 0)


def house_number(text_x: str, pos: int | None) -> str | None:
    """道路前面的门牌号（跳过 BLK / BLOCK / NO 和夹在中间的单元号，如 "Blk 26, #01-192 Teck Whye Ln"）。"""
    if pos is None:
        return None
    toks = text_x.split()[:pos]
    while toks and (toks[-1] in ("BLK", "BLOCK", "NO", "UNIT") or toks[-1].startswith("#")):
        toks.pop()
    if toks and re.fullmatch(r"\d{1,4}[A-Z]?", toks[-1]):
        return toks[-1]
    return None


STREETS: set[str] = set()


def streets_in(text_x: str) -> set[str]:
    """文字里出现的官方道路名（展开缩写后按词组精确查找）。"""
    toks, found = text_x.split(), set()
    for i in range(len(toks)):
        for j in range(i + 1, min(i + 7, len(toks)) + 1):
            if " ".join(toks[i:j]) in STREETS:
                found.add(" ".join(toks[i:j]))
    return found


def analyze(place: dict, by_postal, by_num_street) -> dict | None:
    addr = (place.get("addresses") or [{}])[0]
    ff, pc = addr.get("freeform"), (addr.get("postcode") or "").strip()
    if not ff:
        return None
    text_n = norm(ff)
    text_x = expand(text_n)
    raw = re.sub(r"\s+", " ", ff.upper().replace("\\N", " ")).strip()
    parts = [x.strip() for x in raw.split(",") if len(x.strip()) >= 6]
    out = {"case": case_style(ff), "has_singapore": "SINGAPORE" in text_n,
           "postcode_in_text": bool(re.search(r"(?<!\d)\d{6}(?!\d)", text_n)),
           "unit": bool(UNIT_RE.search(ff)), "blk_prefix": bool(re.search(r"\b(?:BLK|BLOCK)\b", text_n)),
           "unit_forms": [name for name, rx in UNIT_FORMS if rx.search(ff)],
           "duplicated": len(parts) != len(set(parts)),
           "prefix_text": bool(parts) and not re.match(r"^(?:#|BLK|BLOCK|NO\b|\d)", parts[0])}
    if not pc:
        out["postcode"] = "缺失"
        return out
    if not re.fullmatch(r"\d{6}", pc):
        out["postcode"] = "非 6 位（多为马来西亚 / 印尼）" if re.fullmatch(r"\d{5}", pc) else "格式错误"
        return out
    cands = by_postal.get(pc)
    if not cands:
        out["postcode"] = "官方地址表里没有"
        return out
    scored = []
    for num, street, blds in cands:
        form, pos = street_match(text_n, text_x, street)
        written = house_number(text_x, pos)
        rank = {"全称": 3, "缩写": 3, "拼错（可认出）": 2, "没写 / 认不出": 0}[form] + (written == num)
        scored.append((rank, num, street, blds, form, written))
    _, num, street, blds, form, written = max(scored, key=lambda x: x[0])
    out["postcode"] = "有效"
    others = streets_in(text_x) - {norm(s) for _, s, _ in cands}
    if form == "没写 / 认不出" and others:
        # 写了另一条真实道路：邮编指向的是别的地址
        out["postcode"] = "与所写地址矛盾"
        out["example"] = (ff, pc, f"{num} {street}")
        return out
    out["street"] = form
    elsewhere = re.search(rf"(?<![A-Z0-9#\-]){re.escape(num)}(?![A-Z0-9\-])", text_n) if num else None
    out["number"] = ("一致" if written == num else "不同" if written
                     else "写在别处（如道路后面的 Block 177）" if elsewhere else "没写")
    if written and written != num and form != "没写 / 认不出":
        other = by_num_street.get((written, norm(street)))
        if other and pc not in other:
            out["postcode"] = "与所写地址矛盾"  # 写下的门牌 + 道路在官方表里属于另一个邮编
    out["building"] = bool(blds) and any(fuzz.token_set_ratio(norm(b), text_n) >= 90 for b in blds)
    out["hdb"] = _is_hdb(num, pc)
    out["cjk"] = bool(re.search(r"[\u3400-\u9fff]", ff))
    out["example"] = (ff, pc, f"{num} {street}")
    return out


def _is_hdb(num: str, pc: str) -> bool:
    m = re.fullmatch(r"(\d{1,3})([A-H]?)", num or "")
    return bool(m) and pc[3:] == m.group(1).zfill(3) and pc[2] == ("0" if not m.group(2) else str(ord(m.group(2)) - 64))


def summarize(results: list[dict]) -> dict:
    n = len(results)
    rate = lambda pred: sum(1 for r in results if pred(r)) / max(n, 1)  # noqa: E731
    with_pc = [r for r in results if r.get("postcode") in ("有效", "与所写地址矛盾")]
    street_known = [r for r in with_pc if "street" in r]
    dist = lambda rows, k: {v: c / max(len(rows), 1) for v, c in Counter(r.get(k) for r in rows).most_common()}  # noqa: E731
    units = [r for r in results if r["unit"]]
    return {
        "n": n,
        "postcode": dist(results, "postcode"),
        "street": dist(street_known, "street"),
        "number": dist(street_known, "number"),
        "unit_rate": rate(lambda r: r["unit"]),
        "unit_forms": {k: v / max(len(units), 1) for k, v in Counter(f for r in units for f in r["unit_forms"]).items()},
        "blk_prefix": rate(lambda r: r["blk_prefix"]),
        "building": sum(1 for r in with_pc if r.get("building")) / max(len(with_pc), 1),
        "prefix_text": sum(1 for r in with_pc if r.get("prefix_text")) / max(len(with_pc), 1),
        "has_singapore": rate(lambda r: r["has_singapore"]),
        "postcode_in_text": rate(lambda r: r["postcode_in_text"]),
        "duplicated": rate(lambda r: r["duplicated"]),
        "case": dist(results, "case"),
        "n_with_postcode": len(with_pc),
        "cjk": rate(lambda r: r.get("cjk")),
        "hdb": _subset([r for r in with_pc if r.get("hdb")]),
        "non_hdb": _subset([r for r in with_pc if r.get("hdb") is False]),
    }


def _subset(rows: list[dict]) -> dict:
    n = max(len(rows), 1)
    return {"n": len(rows), "blk_prefix": sum(r["blk_prefix"] for r in rows) / n,
            "unit": sum(r["unit"] for r in rows) / n,
            "number_elsewhere": sum(str(r.get("number")).startswith("写在别处") for r in rows) / n,
            "number_missing": sum(r.get("number") == "没写" for r in rows) / n,
            "street_typo": sum(r.get("street") == "拼错（可认出）" for r in rows) / n,
            "postcode_conflict": sum(r.get("postcode") == "与所写地址矛盾" for r in rows) / n}


def abbreviation_usage(places, by_postal) -> dict[str, Counter]:
    """官方全称里的路型词，在商户地址里各被写成什么。"""
    words = ["AVENUE", "STREET", "ROAD", "DRIVE", "CRESCENT", "CENTRAL", "NORTH", "UPPER", "JALAN", "LORONG", "BUKIT"]
    inv = defaultdict(set)
    for k, v in EXPAND.items():
        inv[v].add(k)
    use: dict[str, Counter] = {w: Counter() for w in words}
    for p in places:
        addr = (p.get("addresses") or [{}])[0]
        ff, pc = addr.get("freeform"), addr.get("postcode")
        if not ff or not pc or pc not in by_postal:
            continue
        toks = norm(ff).split()
        streets = {s for _, s, _ in by_postal[pc]}
        for w in words:
            if any(w in s.split() for s in streets):
                if w in toks:
                    use[w]["全称"] += 1
                else:
                    hit = next((a for a in inv[w] if a in toks), None)
                    if hit:
                        use[w][hit] += 1
    return use


def main() -> None:
    by_postal, by_num_street = load_official()
    STREETS.update(norm(s) for rows in by_postal.values() for _, s, _ in rows)
    places = pq.read_table(DATA / "sg_places.parquet", columns=["addresses", "sources"]).to_pylist()
    seen, results_by_src = set(), defaultdict(list)
    for p in places:
        addr = (p.get("addresses") or [{}])[0]
        key = (addr.get("freeform"), addr.get("postcode"))
        if not key[0] or key in seen:  # 同一地址的多家商户只算一次
            continue
        seen.add(key)
        src = next((s["dataset"] for s in p.get("sources") or [] if s["dataset"] != "Overture"), "other")
        r = analyze(p, by_postal, by_num_street)
        if r:
            results_by_src[src].append(r)
    allres = [r for rs in results_by_src.values() for r in rs]
    out = {"all": summarize(allres), **{s: summarize(rs) for s, rs in results_by_src.items() if len(rs) >= 500}}
    out["abbreviation"] = {w: dict(c) for w, c in abbreviation_usage(places, by_postal).items()}
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "noise_stats.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    pct = lambda x: f"{100 * x:.1f}%"  # noqa: E731
    srcs = [s for s in out if s not in ("all", "abbreviation")]
    head = "| 指标 | 全部 | " + " | ".join(srcs) + " |"
    L = ["# 真实人写地址的噪声统计（自动生成）\n",
         f"- 样本：Overture places 里带地址的新加坡商户，按\"地址 + 邮编\"去重后 {out['all']['n']:,} 条；"
         f"标准写法取官方地址表（OpenAddresses sg/countrywide，2026-09）同一邮编下的地址",
         "- 各列为不同来源；Meta 为商户在 Facebook 主页自填，Foursquare 为用户贡献，Microsoft 为聚合数据",
         "- 局限：商户主页地址 ≠ 顾客下单地址，部分由平台自动格式化（缩写风格偏统一）\n",
         "## 邮编\n", head, "|---|---|" + "---|" * len(srcs)]
    for k in ["有效", "缺失", "与所写地址矛盾", "官方地址表里没有", "非 6 位（多为马来西亚 / 印尼）", "格式错误"]:
        L.append(f"| {k} | " + " | ".join(pct(out[s]["postcode"].get(k, 0)) for s in ["all"] + srcs) + " |")
    L += ["\n## 道路写法（邮编有效时，与官方道路比对）\n", head, "|---|---|" + "---|" * len(srcs)]
    for k in ["全称", "缩写", "拼错（可认出）", "没写 / 认不出"]:
        L.append(f"| {k} | " + " | ".join(pct(out[s]["street"].get(k, 0)) for s in ["all"] + srcs) + " |")
    L += ["\n## 门牌号（邮编有效时）\n", head, "|---|---|" + "---|" * len(srcs)]
    for k in ["一致", "写在别处（如道路后面的 Block 177）", "没写", "不同"]:
        L.append(f"| {k} | " + " | ".join(pct(out[s]["number"].get(k, 0)) for s in ["all"] + srcs) + " |")
    L += ["\n## 其他写法\n", head, "|---|---|" + "---|" * len(srcs)]
    for label, key in [("带单元号", "unit_rate"), ("带 Blk / Block 前缀", "blk_prefix"), ("带楼宇名", "building"),
                       ("地址前面有其他文字（楼宇 / 商户名）", "prefix_text"), ("写了 Singapore", "has_singapore"),
                       ("邮编写在地址文字里", "postcode_in_text"), ("有重复片段", "duplicated")]:
        L.append(f"| {label} | " + " | ".join(pct(out[s][key]) for s in ["all"] + srcs) + " |")
    L += ["\n## 组屋 vs 非组屋（邮编有效时；组屋按邮编规则判断）\n", "| 指标 | 组屋 | 非组屋 |", "|---|---|---|"]
    h, o = out["all"]["hdb"], out["all"]["non_hdb"]
    for label, key in [("条数", "n"), ("带 Blk / Block 前缀", "blk_prefix"), ("带单元号", "unit"),
                       ("门牌写在别处", "number_elsewhere"), ("门牌没写", "number_missing"), ("道路拼错", "street_typo"),
                       ("邮编与所写地址矛盾", "postcode_conflict")]:
        L.append(f"| {label} | " + (f"{h[key]:,} | {o[key]:,}" if key == "n" else f"{pct(h[key])} | {pct(o[key])}") + " |")
    L.append(f"\n含中文字符（如\"238号\"）：{pct(out['all']['cjk'])}")
    L += ["\n## 大小写\n", head, "|---|---|" + "---|" * len(srcs)]
    for k in ["首字母大写 / 混合", "全大写", "全小写"]:
        L.append(f"| {k} | " + " | ".join(pct(out[s]["case"].get(k, 0)) for s in ["all"] + srcs) + " |")
    L += ["\n## 单元号写法（带单元号的地址中）\n", "| 写法 | 占比 |", "|---|---|"]
    for k, v in sorted(out["all"]["unit_forms"].items(), key=lambda kv: -kv[1]):
        L.append(f"| {k} | {pct(v)} |")
    L += ["\n## 路型词的写法（官方全称 -> 商户地址里的写法）\n", "| 官方全称 | 写法分布 |", "|---|---|"]
    for w, c in out["abbreviation"].items():
        tot = sum(c.values())
        if tot:
            L.append(f"| {w} | " + "，".join(f"{k} {pct(v / tot)}" for k, v in sorted(c.items(), key=lambda kv: -kv[1]))
                     + f"（{tot:,}） |")
    (ROOT / "reports" / "noise_stats.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
