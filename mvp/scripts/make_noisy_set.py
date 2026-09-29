"""生成"真实客户输入"风格的噪声评测集：地址里混着电话、邮箱、订单号、收件人、公司名、配送备注，
以及本地缩写、粘连 / 标点混乱、多处拼写错误、各种单元号写法。

评测口径（与 docs/04 一致，但针对噪声场景）：
  N1–N8：输入里包含一个真实地址 -> 期望系统识别出这个地址（ACCEPT 或 CONFIRM 都算"可用"），
         且非地址信息不能混进标准化地址；N6（多处拼写错误）期望 CONFIRM
  N9：输入里根本没有可用地址 -> 期望 FIX

噪声样式按新加坡电商 / 物流订单里的常见写法设计；真实分布需用客户数据再校准。
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

from avmvp.reference import ReferenceDB  # noqa: E402
from make_golden_set import abbreviate, typo  # noqa: E402
from avmvp.normalize import match_key, title_case  # noqa: E402

CATEGORIES = {
    "N1_contact_info": "ACCEPT",      # 电话 / 邮箱 / 订单号
    "N2_recipient_company": "ACCEPT",  # 收件人 / 公司名
    "N3_delivery_notes": "ACCEPT",     # 配送备注（中英文）
    "N4_local_abbrev": "ACCEPT",       # AMK / CCK / TPY 等本地缩写
    "N5_glued_punct_case": "ACCEPT",   # 粘连、标点、大小写混乱
    "N6_multi_typo": "CONFIRM",        # 两处拼写错误
    "N7_unit_variants": "ACCEPT",      # 单元号 / 楼层的各种写法
    "N8_mixed_noise": "ACCEPT",        # 多种噪声叠加
    "N9_no_address": "FIX",            # 根本没有地址
}

# 本地缩写（全称 -> 常见写法）；两字母缩写只在后面紧跟路型 / 方位词时才有人这么写
TOWN_ABBR = {
    "ANG MO KIO": ["AMK"], "CHOA CHU KANG": ["CCK"], "TOA PAYOH": ["TPY"], "BUKIT BATOK": ["BB", "BT BATOK"],
    "BUKIT PANJANG": ["BP", "BT PANJANG"], "BUKIT MERAH": ["BT MERAH"], "BUKIT TIMAH": ["BT TIMAH"],
    "JURONG WEST": ["JW"], "JURONG EAST": ["JE"], "TAMPINES": ["TAMP"], "PASIR RIS": ["PR"],
    "SENGKANG": ["SK"], "PUNGGOL": ["PG"], "WOODLANDS": ["WDL"], "SEMBAWANG": ["SBW"], "HOUGANG": ["HG"],
    "SERANGOON": ["SRG"], "YISHUN": ["YS"], "COMMONWEALTH": ["C'WEALTH"],
}
CONTEXT = {"STREET", "AVENUE", "DRIVE", "CENTRAL", "NORTH", "SOUTH", "EAST", "WEST", "ROAD", "CRESCENT",
           "INDUSTRIAL", "RING", "WAY", "WALK", "LINK", "CLOSE", "LANE", "RISE", "VIEW", "LOOP", "PLACE"}

NAMES = ["Tan Ah Kow", "Lim Mei Ling", "Muhammad Faizal", "Rajesh Kumar", "Wong Kai Wen", "Sarah Ng", "Nur Aisyah",
         "Ahmad Hassan", "Chen Wei", "Kavitha R", "Jason Teo", "Goh Siew Lan", "Daniel Lee", "Priya S"]
HONORIFICS = ["Mr", "Ms", "Mdm", "Mrs", "Dr"]
COMPANIES = ["ABC Trading Pte Ltd", "Sunrise Logistics Pte. Ltd.", "Blue Ocean Pte Ltd", "Lim & Co LLP",
             "Evergreen Solutions Pte Ltd", "Kopi Corner Pte. Ltd."]
EMAIL_USERS = ["tan.ahkow", "meiling88", "faizal_m", "sales", "orders", "jason.teo"]
EMAIL_DOMAINS = ["gmail.com", "hotmail.com", "yahoo.com.sg", "company.com.sg"]
NOTES_EN = ["pls call before delivery", "leave at door", "leave with guard house", "call upon arrival",
            "no need to call", "deliver after 6pm", "weekdays only", "fragile pls handle with care",
            "COD", "ring the bell twice", "pass to security", "thanks!", "pls sms when reach", "dont ring doorbell"]
NOTES_CN = ["请放门口", "到了打电话", "放保安室", "周末送", "谢谢", "送到前请联系"]
JUNK = ["same as last order", "pls call me for address", "home", "office", "near the MRT", "TBC", "NA", "-",
        "Singapore", "ask the guard", "my house", "collect at shop", "refer to previous order", "pls whatsapp me"]


def phone(rng):
    num = f"{rng.choice('689')}{rng.randint(0, 9999999):07d}"
    fmt = rng.choice(["{a}{b}", "{a} {b}", "+65 {a} {b}", "+65{a}{b}", "(65) {a}-{b}"])
    label = rng.choice(["", "Tel: ", "HP ", "Mobile: ", "Contact ", "Ph: "])
    return label + fmt.format(a=num[:4], b=num[4:]), num


def email(rng):
    return f"{rng.choice(EMAIL_USERS)}@{rng.choice(EMAIL_DOMAINS)}"


def order_ref(rng):
    return rng.choice([f"Order #SG{rng.randint(2023, 2026)}-{rng.randint(100000, 999999)}",
                       f"PO: 45{rng.randint(10000000, 99999999)}", f"Ref: INV-{rng.randint(10000, 99999)}",
                       f"AWB {rng.randint(10 ** 11, 10 ** 12 - 1)}"])


def base(e, rng, unit=None):
    blk = f"Blk {e.blk}" if rng.random() < 0.3 else e.blk
    parts = [f"{blk} {title_case(e.road)}"]
    if unit:
        parts.append(unit)
    parts.append(rng.choice([f"Singapore {e.postal}", f"S{e.postal}", f"S({e.postal})", e.postal]))
    return ", ".join(parts)


def local_abbrev(e, rng) -> str | None:
    road = e.road
    for full, abbrs in TOWN_ABBR.items():
        if road.startswith(full + " ") or f" {full} " in f" {road} ":
            after = road.split(full, 1)[1].split()
            choices = [a for a in abbrs if len(a) > 2 or (after and after[0] in CONTEXT)]
            if not choices:
                return None
            return road.replace(full, rng.choice(choices), 1)
    return None


def glue_punct_case(text, rng):
    t = text
    if rng.random() < 0.6:
        t = t.replace("Blk ", "Blk", 1) if "Blk " in t else t.replace(" ", "", 1)  # Blk123 / 10Bayfront
    if rng.random() < 0.5:
        t = t.replace(", ", rng.choice([",,", " ;", " - ", ". ", "  "]))
    if rng.random() < 0.5:
        t = "".join(c.upper() if rng.random() < 0.5 else c.lower() for c in t)
    else:
        t = rng.choice([t.lower(), t.upper()])
    return t


def unit_variant(rng):
    f, u = rng.randint(1, 15), rng.randint(1, 350)
    std = f"#{f:02d}-{u:02d}"
    text = rng.choice([std, f"# {f:02d} - {u:02d}", f"{f:02d}-{u:02d}", f"Unit {f:02d}-{u:02d}",
                       f"Unit #{f:02d}-{u:02d}", f"Level {f} Unit {u:02d}", f"Lvl {f} #{u:02d}", f"#{f:02d}-{u:02d}"])
    return text, std


def multi_typo(e, rng) -> str | None:
    words = e.road.split()
    idx = [i for i, t in enumerate(words) if t.isalpha() and len(t) >= 5]
    if not idx:
        return None
    for _ in range(2):
        i = rng.choice(idx)
        words[i] = typo(words[i], rng)
    return " ".join(words)


def add_noise(text, rng, kinds):
    """在地址文本前后插入非地址信息，返回（新文本，注入的电话号码）。"""
    phones = []
    for k in kinds:
        if k == "phone":
            ptxt, num = phone(rng)
            phones.append(num)
            text = f"{text} {ptxt}" if rng.random() < 0.6 else f"{ptxt}, {text}"
        elif k == "email":
            text = f"{text}, {email(rng)}"
        elif k == "order":
            text = f"{order_ref(rng)}, {text}" if rng.random() < 0.5 else f"{text} ({order_ref(rng)})"
        elif k == "recipient":
            name = rng.choice(NAMES)
            head = rng.choice([f"Attn: {name}", f"{rng.choice(HONORIFICS)} {name}", f"c/o {name}", name,
                               f"To: {name}"])
            text = f"{head}, {text}"
        elif k == "company":
            text = f"{rng.choice(COMPANIES)}, {text}"
        elif k == "note":
            note = rng.choice(NOTES_EN) if rng.random() < 0.7 else rng.choice(NOTES_CN)
            text = rng.choice([f"{text} ({note})", f"{text}, {note}", f"{text} - {note}", f"{text} {note}"])
    return text, phones


def build(db, eids, per_cat, rng, prefix):
    ents = [db.entities[i] for i in eids]
    uniq = [e for e in ents if len(db.by_blk_road[(e.blk, e.road_key)]) == 1]
    rows = []

    def add(cat, text, e=None, unit="", phones=(), note=""):
        rows.append({"case_id": f"{prefix}-{len(rows) + 1:05d}", "category": cat, "input": text,
                     "expected_action": CATEGORIES[cat], "expected_eid": "" if e is None else e.eid,
                     "expected_address": "" if e is None else f"{e.blk} {e.road} {e.postal}",
                     "expected_unit": unit, "expected_phones": "|".join(phones), "note": note})

    for e in rng.sample(uniq, per_cat):
        t, ph = add_noise(base(e, rng), rng, rng.sample(["phone", "email", "order"], rng.randint(1, 2)))
        add("N1_contact_info", t, e, phones=ph)
    for e in rng.sample(uniq, per_cat):
        t, _ = add_noise(base(e, rng), rng, [rng.choice(["recipient", "company"])])
        add("N2_recipient_company", t, e)
    for e in rng.sample(uniq, per_cat):
        t, _ = add_noise(base(e, rng), rng, ["note"])
        add("N3_delivery_notes", t, e)

    abbr_pool = [(e, a) for e in uniq if (a := local_abbrev(e, random.Random(e.eid)))]
    for e, _ in rng.sample(abbr_pool, min(per_cat, len(abbr_pool))):
        road = abbreviate(local_abbrev(e, rng), rng)
        blk = f"Blk {e.blk}" if rng.random() < 0.5 else e.blk
        add("N4_local_abbrev", f"{blk} {title_case(road)}, " + rng.choice([f"S{e.postal}", f"Singapore {e.postal}"]),
            e, note=f"{e.road} -> {road}")
    for e in rng.sample(uniq, per_cat):
        add("N5_glued_punct_case", glue_punct_case(base(e, rng), rng), e)

    made = 0
    while made < per_cat:
        e = rng.choice(uniq)
        bad = multi_typo(e, rng)
        if not bad or match_key(bad) in db.by_road:
            continue
        tail = f", Singapore {e.postal}" if rng.random() < 0.5 else ""
        add("N6_multi_typo", f"{e.blk} {title_case(bad)}{tail}", e, note=f"{e.road} -> {bad}")
        made += 1

    for e in rng.sample(uniq, per_cat):
        utext, std = unit_variant(rng)
        add("N7_unit_variants", base(e, rng, unit=utext), e, unit=std)

    for e in rng.sample(uniq, per_cat):
        unit_text, std = unit_variant(rng) if rng.random() < 0.5 else ("", "")
        text = base(e, rng, unit=unit_text or None)
        kinds = rng.sample(["phone", "email", "order", "recipient", "company", "note"], rng.randint(2, 3))
        text, ph = add_noise(text, rng, kinds)
        if rng.random() < 0.5:
            text = glue_punct_case(text, rng)
        add("N8_mixed_noise", text, e, unit=std, phones=ph, note="+".join(kinds))

    for _ in range(per_cat):
        text = rng.choice(JUNK)
        if rng.random() < 0.4:
            text, _ = add_noise(text, rng, [rng.choice(["phone", "recipient", "note"])])
        add("N9_no_address", text)

    rng.shuffle(rows)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", default=str(ROOT / "data" / "reference_sg.csv.gz"))
    ap.add_argument("--per-cat-test", type=int, default=200)
    ap.add_argument("--per-cat-dev", type=int, default=60)
    ap.add_argument("--seed", type=int, default=20261002)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    db = ReferenceDB.load(args.reference)
    rng = random.Random(args.seed)
    ids = list(range(len(db.entities)))
    rng.shuffle(ids)
    cut = len(ids) // 5
    for name, eids, n in (("dev", ids[:cut], args.per_cat_dev), ("test", ids[cut:], args.per_cat_test)):
        rows = build(db, eids, n, random.Random(f"{args.seed}-{name}"), f"N{name.upper()}")
        out = ROOT / "data" / f"noisy_{name}{args.tag}.csv"
        with open(out, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"{name}: {len(rows)} 条 -> {out}  {dict(Counter(r['category'] for r in rows))}")


if __name__ == "__main__":
    main()
