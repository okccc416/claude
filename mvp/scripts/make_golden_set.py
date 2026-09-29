"""生成压力测试集（Golden Set）：按 docs/04 定义的错误类别，从参考库构造输入与"期望结论"。

期望结论按类别语义事先定义（与 docs/04 第 2 节一致），而不是按本方案的输出反推：
  A 标准正确 / B 格式混乱 / I 带单元号          -> ACCEPT
  C 道路拼写错误 / D1 缺邮编 / E 邮编错误 / G 仅楼宇名 -> CONFIRM（并给出正确地址）
  D2 缺楼栋号 / F1 不存在的楼栋号 / F2 不存在的道路     -> FIX

开发集（dev）用于调对照方案的阈值，测试集（test）只用于最终评测，两者使用不相交的地址实体。
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp.normalize import _VARIANTS, match_key, split_alpha_num, title_case  # noqa: E402
from avmvp.reference import ReferenceDB  # noqa: E402

CATEGORIES = {
    "A_clean": "ACCEPT",
    "B_messy_format": "ACCEPT",
    "C_street_typo": "CONFIRM",
    "D1_missing_postcode": "CONFIRM",
    "D2_missing_block": "FIX",
    "E_wrong_postcode": "CONFIRM",
    "F1_nonexistent_block": "FIX",
    "F2_nonexistent_street": "FIX",
    "G_building_name_only": "CONFIRM",
    "I_with_unit": "ACCEPT",
}

# 全称 -> 口语里常见的缩写写法（用于构造"格式混乱"样本）
_SHORT = {vs[0]: [v for v in vs[1:] if v != "SAINT"] for vs in _VARIANTS.values()}


def abbreviate(road: str, rng: random.Random) -> str:
    out = []
    for t in road.split():
        alts = _SHORT.get(t)
        out.append(rng.choice(alts) if alts and rng.random() < 0.8 else t)
    return " ".join(out)


def typo(word: str, rng: random.Random) -> str:
    i = rng.randrange(1, len(word) - 1)
    op = rng.choice(["sub", "del", "ins", "swap"])
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if op == "sub":
        return word[:i] + rng.choice(letters.replace(word[i], "")) + word[i + 1:]
    if op == "del":
        return word[:i] + word[i + 1:]
    if op == "ins":
        return word[:i] + rng.choice(letters) + word[i:]
    return word[: i - 1] + word[i] + word[i - 1] + word[i + 1:] if word[i] != word[i - 1] else word[:i] + "X" + word[i + 1:]


def fmt_clean(e, rng, building=True) -> str:
    parts = [f"{e.blk} {title_case(e.road)}"]
    if building and e.primary_building and rng.random() < 0.5:
        parts.append(title_case(e.primary_building))
    parts.append(f"Singapore {e.postal}")
    return ", ".join(parts)


def fmt_messy(e, rng) -> str:
    road = abbreviate(e.road, rng) if rng.random() < 0.7 else e.road
    blk = f"Blk {e.blk}" if rng.random() < 0.4 else e.blk
    postal_fmt = rng.choice(["S{p}", "S({p})", "Singapore {p}", "SG {p}", "S'pore {p}", "{p}"])
    if e.postal.startswith("0") and rng.random() < 0.15:
        postal = postal_fmt.format(p=e.postal[1:])  # 表格软件吞掉前导 0
    else:
        postal = postal_fmt.format(p=e.postal)
    parts = [f"{blk} {road}", postal]
    if rng.random() < 0.3:
        parts.reverse()
    sep = rng.choice([", ", " ", "  ", ","])
    text = sep.join(parts)
    case = rng.random()
    if case < 0.4:
        text = text.lower()
    elif case < 0.6:
        text = text.upper()
    else:
        text = title_case(text)
    return text


def build(db: ReferenceDB, eids: list[int], per_cat: int, rng: random.Random, prefix: str) -> list[dict]:
    ents = [db.entities[i] for i in eids]
    unique_br = [e for e in ents if len(db.by_blk_road[(e.blk, e.road_key)]) == 1]
    multi_roads = sorted({e.road_key for e in ents if len(db.by_road[e.road_key]) >= 3})
    all_roads = list(db.by_road)
    vocab = sorted({t for r in all_roads for t in split_alpha_num(r)[0].split() if len(t) >= 4})

    rows: list[dict] = []

    def add(cat, text, eid=None, unit=None, note=""):
        rows.append({
            "case_id": f"{prefix}-{len(rows) + 1:05d}", "category": cat, "input": text,
            "expected_action": CATEGORIES[cat], "expected_eid": "" if eid is None else eid,
            "expected_address": "" if eid is None else f"{db.entities[eid].blk} {db.entities[eid].road} {db.entities[eid].postal}",
            "expected_unit": unit or "", "note": note,
        })

    for e in rng.sample(unique_br, per_cat):
        add("A_clean", fmt_clean(e, rng), e.eid)
    for e in rng.sample(unique_br, per_cat):
        add("B_messy_format", fmt_messy(e, rng), e.eid)

    pool = [e for e in unique_br if any(len(t) >= 5 and t.isalpha() for t in e.road.split())]
    made = 0
    while made < per_cat:
        e = rng.choice(pool)
        words = e.road.split()
        idx = rng.choice([i for i, t in enumerate(words) if len(t) >= 5 and t.isalpha()])
        words[idx] = typo(words[idx], rng)
        bad = " ".join(words)
        if match_key(bad) in db.by_road:
            continue
        text = f"{e.blk} {title_case(bad)}" + (f", Singapore {e.postal}" if rng.random() < 0.5 else "")
        add("C_street_typo", text, e.eid, note=f"{e.road} -> {bad}")
        made += 1

    for e in rng.sample(unique_br, per_cat):
        add("D1_missing_postcode", f"{e.blk} {title_case(e.road)}", e.eid)

    for rk in rng.sample(multi_roads, min(per_cat, len(multi_roads))):
        add("D2_missing_block", f"{title_case(db.road_display[rk])}, Singapore")

    made = 0
    while made < per_cat:
        e = rng.choice(unique_br)
        other = db.entities[rng.randrange(len(db.entities))]
        if other.road_key == e.road_key or other.postal == e.postal:
            continue
        add("E_wrong_postcode", f"{e.blk} {title_case(e.road)}, Singapore {other.postal}", e.eid,
            note=f"postal {other.postal} belongs to {other.blk} {other.road}")
        made += 1

    made = 0
    while made < per_cat:
        rk = rng.choice(multi_roads)
        blks = {db.entities[i].blk for i in db.by_road[rk]}
        n = str(rng.randint(1, 999))
        if n in blks or any(b.rstrip("ABCDEFGH") == n for b in blks):
            continue
        add("F1_nonexistent_block", f"{n} {title_case(db.road_display[rk])}, Singapore", note="block not on street")
        made += 1

    made = 0
    while made < per_cat:
        base = db.entities[rng.randrange(len(db.entities))].road
        words = base.split()
        alpha_idx = [i for i, t in enumerate(words) if t.isalpha() and len(t) >= 4]
        if not alpha_idx:
            continue
        for i in alpha_idx:
            words[i] = rng.choice(vocab)
        fake = " ".join(words)
        toks = match_key(fake).split()
        if db.find_roads(toks, min_score=80) or db.find_building_entities(toks):
            continue
        add("F2_nonexistent_street", f"{rng.randint(1, 300)} {title_case(fake)}, Singapore", note="street does not exist")
        made += 1

    gpool = []
    for e in ents:
        for b in e.buildings:
            k = match_key(b)
            if (len(k.split()) >= 2 and k not in db.by_road and db.by_building[k] == [e.eid]
                    and db.find_building_entities(k.split()) == [e.eid]):
                gpool.append((e, b))
                break
    for e, b in rng.sample(gpool, min(per_cat, len(gpool))):
        add("G_building_name_only", title_case(b), e.eid)

    for e in rng.sample(unique_br, per_cat):
        unit = f"#{rng.randint(1, 12):02d}-{rng.randint(1, 999):02d}"
        add("I_with_unit", f"{e.blk} {title_case(e.road)} {unit}, Singapore {e.postal}", e.eid, unit=unit)

    rng.shuffle(rows)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", default=str(ROOT / "data" / "reference_sg.csv.gz"))
    ap.add_argument("--per-cat-test", type=int, default=400)
    ap.add_argument("--per-cat-dev", type=int, default=100)
    ap.add_argument("--seed", type=int, default=20261001)
    ap.add_argument("--tag", default="", help="输出文件名后缀，如 --tag _iter 生成 golden_test_iter.csv")
    args = ap.parse_args()

    db = ReferenceDB.load(args.reference)
    rng = random.Random(args.seed)
    ids = list(range(len(db.entities)))
    rng.shuffle(ids)
    cut = len(ids) // 5
    dev_ids, test_ids = ids[:cut], ids[cut:]

    for name, eids, n in (("dev", dev_ids, args.per_cat_dev), ("test", test_ids, args.per_cat_test)):
        rows = build(db, eids, n, random.Random(f"{args.seed}-{name}"), name.upper())
        out = ROOT / "data" / f"golden_{name}{args.tag}.csv"
        with open(out, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"{name}: {len(rows)} 条 -> {out}  {dict(Counter(r['category'] for r in rows))}")


if __name__ == "__main__":
    main()
