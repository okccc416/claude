"""按"调研 + 实测"得到的噪声种类和比例，在 2026 年官方地址表上构造测试集。

与 make_labeled_orders.py 的区别：
1. 标准地址来自 2026 年的官方地址表（OneMap 地址经 OpenAddresses / Overture 发布，scripts/fetch_overture.py 下载），
   不是校验器使用的 2017 年参考库。2026 表里有、参考库里没有的地址，就是**真实的新地址**，不再虚构
2. 每一种噪声的比例都有出处（NOISE 表），分三类：
     实测 —— scripts/measure_noise.py 在 10.6 万条新加坡商户自填地址上的统计（reports/noise_stats.md）
     文献 —— Baymard（手输地址错拼率）、Damerau（字母错拼的构成）、Verhoeff（数字输入错误的构成）、SingStat（住房结构）
     假设 —— 没有找到数据的项，单独标出，便于日后用真实订单替换
3. 不按渠道模拟，而是按单个字段独立注入（每种噪声的出现概率 = 表中比例）

标注规则、期望结论与 make_labeled_orders.py 完全一致（同一套标注规范），输出格式也一致，可直接用 evaluate_labeled.py 评测。

  python scripts/fetch_overture.py              # 先下载 2026 年地址表
  python scripts/make_research_testset.py       # 默认 5,000 条 -> labeled/testset_sg_research_v1.csv
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from avmvp.reference import ReferenceDB  # noqa: E402
from make_labeled_orders import (  # noqa: E402
    KEYBOARD, MISLEADING, MY_CITIES, MY_NAMES, NAMES, NO_ADDRESS, NO_ADDRESS_TEXTS, NOT_IN_REFERENCE, NOTES,
    NUMPAD, OUT_OF_REGION, RESOLVABLE, World, Written, digits, gold_action, is_hdb, make_unit, resolve, std_unit,
    title, weighted,
)

# ---------------------------------------------------------------------------------------------- 噪声比例与出处
# (比例, 依据类型, 出处 / 说明)。实测数字见 reports/noise_stats.md
NOISE: dict[str, tuple] = {
    "no_address": (0.005, "假设", "没有可投递地址（自取、\"同上次\"）"),
    "out_of_region": (0.005, "假设", "马来西亚（柔佛）地址"),
    "postal_missing": (0.035, "实测", "商户地址邮编缺失 3.5%（Meta 1.9% ~ Foursquare 18.2%）"),
    "postal_wrong": (0.045, "实测", "邮编与所写门牌道路矛盾 3.0% + 官方表里查无此邮编 1.5%"),
    "postal_wrong_neighbour": (0.5, "假设", "错误邮编中一半是相邻门牌的邮编（抽检样例多为此类），一半是按键错误"),
    "number_missing": (0.052, "实测", "门牌没写 5.2%"),
    "number_wrong": (0.026, "实测", "门牌与邮编对应的官方门牌不同 2.6%"),
    "number_letter_drop": (0.4, "假设", "带字母后缀的楼号写错时，四成是漏写后缀（如 7A 写成 7，抽检中常见）"),
    "number_after_street_hdb": (0.042, "实测", "组屋门牌写在道路后面（Hougang Ave 2, Block 706）4.2%"),
    "number_after_street_other": (0.024, "实测", "非组屋 2.4%"),
    "street_typo": (0.05, "文献 + 实测", "Baymard：手输地址 9% 含错拼（道路 / 城市 / 门牌）；"
                                        "实测商户地址道路错拼 1.1%（部分经平台格式化，是下限）；取 5%"),
    "building_only": (0.038, "实测", "道路没写 / 认不出 3.8%，多为只写楼宇 / 商场名（#B1-23 Junction 8）"),
    "blk_prefix_hdb": (0.214, "实测", "组屋地址带 Blk / Block 前缀 21.4%"),
    "blk_prefix_other": (0.021, "实测", "非组屋 2.1%"),
    "unit_missing": (0.10, "假设", "没找到订单级比例；文献只说明缺单元号 / 门牌约占派送失败的 30%"),
    "unit_before_address": (0.2, "假设", "单元号写在门牌前面（#01-07 36 Armenian Street）"),
    "building_with_address": (0.331, "实测", "带楼宇名 33.1%"),
    "building_before_address": (0.44, "实测", "楼宇名写在地址前面 14.7%（占带楼宇名的 44%）"),
    "duplicated": (0.002, "实测", "有重复片段 0.2%"),
    "cjk": (0.005, "实测", "夹杂中文（238号）0.5%"),
    "noise_text": (0.05, "假设", "地址栏里混入姓名 / 电话 / 备注"),
    "postal_with_singapore": (0.5, "假设", "邮编前写 Singapore 的比例（格式）"),
}
# 大小写（实测：商户地址首字母大写 / 混合 98.8%、全大写 0.6%、全小写 0.4%）
CASE = {"as_is": 98.8, "upper": 0.6, "lower": 0.4}
# 单元号写法（实测，带单元号的地址中）
UNIT_FORMS = [("{f}-{n}#", 90.1), ("level", 3.4), ("spaced", 2.3), ("unit", 1.0), ("nozero", 0.1)]
# 路型词缩写（实测：官方全称在商户地址里被写成缩写的比例）
ABBREV = {"AVENUE": [("Ave", 87.3), (None, 11.3), ("Av", 1.4)], "STREET": [("St", 65.0), (None, 35.0)],
          "ROAD": [("Rd", 89.3), (None, 10.7)], "DRIVE": [("Dr", 81.3), (None, 18.7)],
          "CRESCENT": [("Cres", 87.6), (None, 12.4)], "CENTRAL": [(None, 99.9), ("Ctrl", 0.1)],
          "NORTH": [(None, 70.9), ("N", 28.9), ("Nth", 0.2)], "UPPER": [(None, 83.0), ("Upp", 17.0)],
          "JALAN": [("Jln", 60.8), (None, 39.2)], "LORONG": [("Lor", 80.4), (None, 19.5), ("Lrg", 0.1)],
          "BUKIT": [(None, 99.4), ("Bt", 0.6)]}
# 字母错拼的构成（文献：Damerau 1964，80% 以上是单次编辑；四种编辑的比例为假设）
LETTER_TYPO = {"single": 0.8, "ops": {"substitute": 40, "delete": 25, "insert": 20, "transpose": 15}}
# 数字输入错误的构成（文献：Verhoeff 1969，单个数字错 79.1%、相邻对调 10.2%、其他 10.7%）
DIGIT_TYPO = {"single": 79.1, "adjacent_transposition": 10.2, "other": 10.7}
# 住房结构（文献：SingStat 2024，常住户 77.4% 住组屋、17.7% 住公寓、4.7% 住有地住宅）；送到公司的比例为假设
PTYPE_MIX = {"HDB": 0.85 * 77.4, "CONDO": 0.85 * 17.7, "LANDED": 0.85 * 4.7, "COMMERCIAL": 15.0}


# ---------------------------------------------------------------------------------------------- 错误模型
def letter_typo(word: str, rng: random.Random) -> str:
    """Damerau：大多数错拼是一次插入 / 删除 / 替换 / 相邻对调；少数是两次。保证结果与原词不同。"""
    for _ in range(10):
        out = _letter_typo_once(word, rng)
        if out != word:
            return out
    return out


def _letter_typo_once(word: str, rng: random.Random) -> str:
    out = word
    for _ in range(1 if rng.random() < LETTER_TYPO["single"] else 2):
        idx = [i for i, c in enumerate(out) if c.isalpha()][1:]  # 首字母很少打错
        if len(idx) < 3:
            return out
        i = rng.choice(idx)
        op = weighted(rng, LETTER_TYPO["ops"])
        if op == "substitute":
            out = out[:i] + rng.choice(KEYBOARD.get(out[i], "AEIOU")) + out[i + 1:]
        elif op == "delete":
            out = out[:i] + out[i + 1:]
        elif op == "insert":
            out = out[:i] + (out[i] if rng.random() < 0.5 else rng.choice(KEYBOARD.get(out[i], "E"))) + out[i:]
        elif i + 1 < len(out) and out[i + 1].isalpha() and out[i] != out[i + 1]:
            out = out[:i] + out[i + 1] + out[i] + out[i + 2:]
        else:
            out = out[:i] + out[i + 1:]
    return out


def digit_typo(s: str, rng: random.Random) -> str:
    """Verhoeff：单个数字错（多为相邻键）、相邻两位对调、其他（两位都错 / 隔位对调）。"""
    pos = [i for i, c in enumerate(s) if c.isdigit()]
    kind = weighted(rng, DIGIT_TYPO)
    if kind == "adjacent_transposition":
        pairs = [i for i in pos if i + 1 in pos and s[i] != s[i + 1]]
        if pairs:
            i = rng.choice(pairs)
            return s[:i] + s[i + 1] + s[i] + s[i + 2:]
        kind = "single"
    chars = list(s)
    for i in rng.sample(pos, 1 if kind == "single" or len(pos) < 2 else 2):
        chars[i] = rng.choice(NUMPAD[chars[i]])
    return "".join(chars)


def road_typo(road: str, rng: random.Random) -> str:
    words = road.split()
    cand = [i for i, w in enumerate(words) if w.isalpha() and len(w) >= 4 and w not in ABBREV]
    cand = cand or [i for i, w in enumerate(words) if w.isalpha() and len(w) >= 4]
    if not cand:
        return road
    i = rng.choice(cand)
    words[i] = letter_typo(words[i], rng)
    return " ".join(words)


def abbreviate(road: str, rng: random.Random, tags: list[str]) -> str:
    out = []
    for w in road.split():
        alt = weighted(rng, ABBREV[w]) if w in ABBREV else None
        if alt:
            tags.append("ABBREV")
        out.append(alt or title(w))
    return " ".join(out)


def fmt_unit(u: tuple[str, str], rng: random.Random, tags: list[str]) -> str:
    f, n = u
    form = weighted(rng, UNIT_FORMS)
    if f.startswith("B") and form in ("level", "nozero"):
        form = "{f}-{n}#"
    if form != "{f}-{n}#":
        tags.append("UNIT_FORMAT")
    if form == "level":
        return f"Level {int(f)} Unit {n}"
    if form == "spaced":
        return f"# {f} - {n}"
    if form == "unit":
        return f"Unit {f}-{n}"
    if form == "nozero":
        return f"#{int(f)}-{n}"
    return f"#{f}-{n}"


# ---------------------------------------------------------------------------------------------- 数据
def load_current_db(path: Path) -> ReferenceDB:
    """2026 年官方地址表（按 门牌 + 道路 + 邮编 聚合，楼宇名合并）。"""
    rows = pq.read_table(path, columns=["street", "number", "unit", "postcode", "bbox"]).to_pylist()
    agg: dict[tuple[str, str, str], dict] = {}
    for r in rows:
        if not r["street"] or not r["postcode"] or not r["number"]:
            continue
        key = (str(r["number"]).upper(), r["street"].upper(), r["postcode"])
        a = agg.setdefault(key, {"blk": key[0], "road": key[1], "postal": key[2], "b": [],
                                 "lat": r["bbox"]["ymin"], "lng": r["bbox"]["xmin"]})
        if r["unit"] and r["unit"] != "NIL" and r["unit"] not in a["b"]:
            a["b"].append(r["unit"])
    return ReferenceDB.from_rows({**a, "buildings": "|".join(a["b"])} for a in agg.values())


class Builder:
    def __init__(self, world: World, ref2017: ReferenceDB, seed: int):
        self.w, self.rng = world, random.Random(seed)
        self.ref_ids = {(e.blk, e.road_key, e.postal): e.eid for e in ref2017.entities}
        self.by_type = {t: ids for t, ids in world.by_type.items()}
        # "只写楼宇名"只可能发生在有楼宇名的地址上：按抽样估计这类地址的占比，把总体比例换算成条件概率
        probe = random.Random(seed + 1)
        has = sum(bool(self._bname(world.db.entities[probe.choice(self.by_type[weighted(probe, PTYPE_MIX)])]))
                  for _ in range(3000)) / 3000
        self.p_building_only = min(1.0, NOISE["building_only"][0] / max(has, 1e-9))

    def _bname(self, e) -> str | None:
        return self.w.building_name(e) if self.w.ptype[e.eid] in ("CONDO", "COMMERCIAL") else None

    def neighbour_postal(self, e) -> str | None:
        """同一条路上门牌最接近、邮编不同的地址的邮编。"""
        db = self.w.db
        num = int(digits(e.blk) or 0)
        others = [db.entities[i] for i in db.by_road[e.road_key] if db.entities[i].postal != e.postal]
        if not others:
            return None
        return min(others, key=lambda x: (abs(int(digits(x.blk) or 0) - num), x.blk)).postal

    def address(self) -> dict:
        rng, db, world = self.rng, self.w.db, self.w
        ptype = weighted(rng, PTYPE_MIX)
        e = db.entities[rng.choice(self.by_type[ptype])]
        hdb = is_hdb(e)
        unit = make_unit(ptype, rng)
        bname = self._bname(e)
        tags: list[str] = []
        st = {"blk": "ok", "street": "ok", "postal": "ok", "building": "absent", "unit": "ok" if unit else "n/a"}
        w = Written(blk=e.blk, road=e.road, postal=e.postal, unit=unit)

        # 门牌 / 道路
        building_only = bool(bname) and rng.random() < self.p_building_only
        if building_only:
            w.blk = w.road = None
            w.building = bname
            st.update(blk="missing", street="missing", building="ok")
            tags.append("BUILDING_ONLY")
        else:
            r = rng.random()
            if r < NOISE["number_missing"][0]:
                w.blk = None
                st["blk"] = "missing"
                tags.append("BLOCK_MISSING")
            elif r < NOISE["number_missing"][0] + NOISE["number_wrong"][0]:
                if e.blk[-1:].isalpha() and rng.random() < NOISE["number_letter_drop"][0]:
                    w.blk, st["blk"] = digits(e.blk), "letter_dropped"
                    tags.append("BLOCK_LETTER_DROPPED")
                else:
                    w.blk, st["blk"] = digit_typo(e.blk, rng), "typo"
                    tags.append("BLOCK_TYPO")
            if rng.random() < NOISE["street_typo"][0]:
                bad = road_typo(e.road, rng)
                if bad != e.road:
                    w.road, st["street"] = bad, "typo"
                    tags.append("STREET_TYPO")
            if bname and rng.random() < NOISE["building_with_address"][0]:
                w.building, st["building"] = bname, "ok"
        # 邮编
        r = rng.random()
        if r < NOISE["postal_missing"][0]:
            w.postal, st["postal"] = None, "missing"
            tags.append("POSTAL_MISSING")
        elif r < NOISE["postal_missing"][0] + NOISE["postal_wrong"][0]:
            nb = self.neighbour_postal(e) if rng.random() < NOISE["postal_wrong_neighbour"][0] else None
            if nb:
                w.postal, st["postal"] = nb, "other_address"
                tags.append("POSTAL_OTHER_ADDRESS")
            else:
                w.postal = digit_typo(e.postal, rng)
                st["postal"] = "typo_valid" if w.postal in world.postals else "typo_invalid"
                tags.append("POSTAL_TYPO")
        # 单元号
        if unit and rng.random() < NOISE["unit_missing"][0]:
            w.unit, st["unit"] = None, "missing"
            tags.append("UNIT_MISSING")
        w.states = st
        text = self.render(w, e, hdb, tags)

        label, rid, why = resolve(world, w)
        if label == RESOLVABLE and world.addr[rid] != world.addr[e.eid]:
            x = db.entities[rid]
            label, why = MISLEADING, f"{why}；但指向 {x.blk} {x.road} {x.postal}，不是真实地址"
        eid17 = self.ref_ids.get((e.blk, e.road_key, e.postal))
        if eid17 is None:
            label, why = NOT_IN_REFERENCE, "2026 年官方地址表里有、2017 年参考库里没有的真实新地址"
            tags.append("NEW_ADDRESS_2026")
        unit_required = ptype in ("HDB", "CONDO", "COMMERCIAL")
        gold, ok = gold_action(label, tags, unit_required and "UNIT_MISSING" in tags)
        return {"channel": "research_mix", "address_line1": text, "address_line2": "", "postal_field": "",
                "input": text, "truth_eid": "" if eid17 is None else eid17, "truth_blk": e.blk,
                "truth_street": e.road, "truth_postal": e.postal, "truth_building": bname or "",
                "truth_unit": std_unit(unit), "property_type": ptype, "unit_required": "Y" if unit_required else "N",
                "text_resolution": label, "gold_action": gold, "acceptable_actions": "|".join(ok),
                "error_tags": "|".join(dict.fromkeys(tags)),
                "field_states": ";".join(f"{k}={v}" for k, v in st.items()), "label_note": why}

    def render(self, w: Written, e, hdb: bool, tags: list[str]) -> str:
        rng = self.rng
        street = abbreviate(w.road, rng, tags) if w.road else ""
        if w.building and not w.road:
            core = title(w.building)
        elif w.blk is None:
            core = street
        elif rng.random() < NOISE["cjk"][0]:
            core = f"{street}, {w.blk}号"
            tags.append("CJK_MIXED")
        elif rng.random() < NOISE["number_after_street_hdb" if hdb else "number_after_street_other"][0]:
            core = f"{street}, Block {w.blk}" if hdb else f"{street} {w.blk}"
            tags.append("NUMBER_AFTER_STREET")
        else:
            if rng.random() < NOISE["blk_prefix_hdb" if hdb else "blk_prefix_other"][0]:
                core = f"{rng.choice(['Blk', 'Block', 'BLK'])} {w.blk} {street}"
            else:
                core = f"{w.blk} {street}"
        parts = [core]
        if w.unit:
            u = fmt_unit(w.unit, rng, tags)
            parts = [f"{u} {core}"] if rng.random() < NOISE["unit_before_address"][0] else [core, u]
        if w.building and w.road:
            if rng.random() < NOISE["building_before_address"][0]:
                parts.insert(0, title(w.building))
                tags.append("BUILDING_PREFIX")
            else:
                parts[-1] = f"{parts[-1]} {title(w.building)}"
        if rng.random() < NOISE["duplicated"][0]:
            parts.append(parts[0])
            tags.append("DUPLICATED_TEXT")
        if w.postal:
            parts.append(f"Singapore {w.postal}" if rng.random() < NOISE["postal_with_singapore"][0] else w.postal)
        text = ", ".join(parts)
        if rng.random() < NOISE["noise_text"][0]:
            name, ph = rng.choice(NAMES), f"{rng.choice('89')}{rng.randint(0, 9999999):07d}"
            kind = rng.choice(["name", "phone", "note"])
            text = {"name": f"{name}, {text}", "phone": f"{text} HP {ph[:4]} {ph[4:]}",
                    "note": f"{text} ({rng.choice(NOTES)})"}[kind]
            tags.append({"name": "NOISE_NAME", "phone": "NOISE_PHONE", "note": "NOISE_NOTE"}[kind])
        style = weighted(rng, CASE)
        return text.upper() if style == "upper" else text.lower() if style == "lower" else text

    def special(self, kind: str) -> dict:
        rng = self.rng
        if kind == "no_address":
            text, label, tags = rng.choice(NO_ADDRESS_TEXTS), NO_ADDRESS, ["NO_ADDRESS"]
            note, postal = "没有可投递的地址", ""
        else:
            city, pre = rng.choice(MY_CITIES)
            taman, postal = rng.choice(MY_NAMES), pre + f"{rng.randint(0, 999):03d}"
            text = f"No. {rng.randint(1, 80)}, Jalan {taman} {rng.randint(1, 12)}/{rng.randint(1, 9)}, " \
                   f"Taman {taman}, {postal} {city}, Johor"
            label, tags, note = OUT_OF_REGION, ["OUT_OF_REGION"], "马来西亚（柔佛）地址"
        gold, ok = gold_action(label, tags, False)
        return {"channel": "research_mix", "address_line1": text, "address_line2": "", "postal_field": "",
                "input": text, "truth_eid": "", "truth_blk": "", "truth_street": "", "truth_postal": postal,
                "truth_building": "", "truth_unit": "", "property_type": "", "unit_required": "N",
                "text_resolution": label, "gold_action": gold, "acceptable_actions": "|".join(ok),
                "error_tags": "|".join(tags), "field_states": "", "label_note": note}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--current", default=str(ROOT / "data" / "overture" / "sg_address.parquet"))
    ap.add_argument("--reference", default=str(ROOT / "data" / "reference_sg.csv.gz"))
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20261101)
    ap.add_argument("--out", default=str(ROOT / "labeled" / "testset_sg_research_v1.csv"))
    args = ap.parse_args()
    world = World(load_current_db(Path(args.current)))
    b = Builder(world, ReferenceDB.load(args.reference), args.seed)
    rows = []
    for k in range(args.n):
        r = b.rng.random()
        if r < NOISE["no_address"][0]:
            row = b.special("no_address")
        elif r < NOISE["no_address"][0] + NOISE["out_of_region"][0]:
            row = b.special("out_of_region")
        else:
            row = b.address()
        rows.append({"order_id": f"RT-{k + 1:05d}", "split": "test", **row})
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    print(f"{len(rows)} 条 -> {out}（2026 地址表 {len(world.db.entities):,} 个地址）")
    for col in ("property_type", "text_resolution", "gold_action"):
        print(f"  {col}: {dict(Counter(r[col] for r in rows).most_common())}")
    tags = Counter(t for r in rows for t in r["error_tags"].split("|") if t)
    print(f"  error_tags: {dict(tags.most_common())}")
    substantive = sum(1 for r in rows if any(t in r["error_tags"] for t in (
        "POSTAL_", "BLOCK_", "STREET_TYPO", "BUILDING_ONLY", "UNIT_MISSING")))
    print(f"  至少有一处需要改动地址的错误：{substantive / len(rows):.1%}")


if __name__ == "__main__":
    main()
