"""用真实人写的地址字符串评测校验器：新加坡商户在 Meta / Foursquare 等平台自填的地址（Overture places）。

构造测试集时的噪声再怎么贴近真实，也是"想得到的"噪声；这里直接用真实字符串检验。
标准答案：只保留"邮编在 2026 年官方地址表里只对应一个地址，且文字里的门牌 / 道路与之不矛盾"的记录，
这样真实地址可以由邮编确定（弱标注，但可靠）。邮编打错这类情况因此不在本测试里（见 make_research_testset.py）。

两种输入：
  带邮编   = 商户填写的地址 + ", Singapore " + 邮编（和结账表单一样，邮编单独一栏）
  不带邮编 = 只有商户填写的地址文字（检验解析真实写法的能力：楼宇名、单元号、缩写、门牌位置 ……）

  python scripts/evaluate_real_strings.py [--n 8000]
输出：reports/real_strings_eval.md、reports/real_strings_eval.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from avmvp import ReferenceDB, Validator  # noqa: E402
from avmvp.normalize import match_key  # noqa: E402
from avmvp.validator import ACCEPT, ADD_SUB  # noqa: E402
import measure_noise as mn  # noqa: E402


def build_cases(n: int, seed: int) -> list[dict]:
    by_postal, by_num_street = mn.load_official()
    mn.STREETS.update(mn.norm(s) for rows in by_postal.values() for _, s, _ in rows)
    places = pq.read_table(mn.DATA / "sg_places.parquet", columns=["addresses", "sources"]).to_pylist()
    seen, cases = set(), []
    for p in places:
        addr = (p.get("addresses") or [{}])[0]
        ff, pc = addr.get("freeform"), (addr.get("postcode") or "").strip()
        if not ff or (ff, pc) in seen or len(by_postal.get(pc, [])) != 1:
            continue
        seen.add((ff, pc))
        r = mn.analyze(p, by_postal, by_num_street)
        if not r or r.get("postcode") != "有效" or r.get("number") == "不同":
            continue
        num, street, _ = by_postal[pc][0]
        src = next((s["dataset"] for s in p.get("sources") or [] if s["dataset"] != "Overture"), "other")
        cases.append({"freeform": " ".join(ff.replace("\\n", " ").split()), "postcode": pc, "truth_blk": num,
                      "truth_street": street, "source": src, "street_form": r.get("street"),
                      "number_form": r.get("number"), "unit": r["unit"], "building": r.get("building"),
                      "prefix_text": r["prefix_text"], "blk_prefix": r["blk_prefix"], "cjk": r.get("cjk")})
    random.Random(seed).shuffle(cases)
    return cases[:n]


def features(c: dict) -> list[str]:
    f = [f"道路：{c['street_form']}", f"门牌：{c['number_form']}"]
    f += ["带单元号"] if c["unit"] else []
    f += ["带楼宇名"] if c["building"] else []
    f += ["地址前有楼宇 / 商户名"] if c["prefix_text"] else []
    f += ["带 Blk 前缀"] if c["blk_prefix"] else []
    f += ["夹杂中文"] if c["cjk"] else []
    return f


def judge(res, key: tuple[str, str, str], in_ref: bool) -> str:
    if res.entity is None:
        return "判 FIX" if in_ref else "正确拒绝（参考库没有）"
    got = (res.entity.blk, res.entity.road_key, res.entity.postal)
    if got == key:
        return "找对 · 直接通过" if res.action in (ACCEPT, ADD_SUB) else "找对 · 要求确认"
    return "静默错误" if res.action in (ACCEPT, ADD_SUB) else "错误建议"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8000)
    ap.add_argument("--seed", type=int, default=20261102)
    ap.add_argument("--reference", default=str(ROOT / "data" / "reference_sg.csv.gz"))
    args = ap.parse_args()
    t0 = time.time()
    cases = build_cases(args.n, args.seed)
    db = ReferenceDB.load(args.reference)
    v = Validator(db)
    ref_keys = {(e.blk, e.road_key, e.postal) for e in db.entities}
    outcomes = {"带邮编": [], "不带邮编": []}
    for c in cases:
        key = (c["truth_blk"], match_key(c["truth_street"]), c["postcode"])
        c["in_ref"] = key in ref_keys
        for mode, text in (("带邮编", f"{c['freeform']}, Singapore {c['postcode']}"), ("不带邮编", c["freeform"])):
            res = v.validate(text)
            got = f"{res.entity.blk} {res.entity.road} {res.entity.postal}" if res.entity else "—"
            outcomes[mode].append((c, judge(res, key, c["in_ref"]), res.action, got, text))
    print(f"{len(cases)} 条真实地址，{time.time() - t0:.0f}s")

    order = ["找对 · 直接通过", "找对 · 要求确认", "判 FIX", "正确拒绝（参考库没有）", "错误建议", "静默错误"]
    pct = lambda x, n: f"{100 * x / max(n, 1):.1f}%"  # noqa: E731
    in_ref = [c for c in cases if c["in_ref"]]
    L = ["# 真实人写地址评测（自动生成）\n",
         f"- 样本：Overture places 中新加坡商户自填地址 {len(cases):,} 条（按\"地址 + 邮编\"去重后随机抽样）；"
         f"其中 {len(in_ref):,} 条的真实地址在 2017 参考库里，{len(cases) - len(in_ref):,} 条是参考库没有的新地址",
         "- 标准答案：邮编在 2026 年官方地址表里只对应一个地址、且文字里的门牌 / 道路不与之矛盾的记录（弱标注）",
         "- 来源构成：" + "，".join(f"{k} {v:,}" for k, v in Counter(c["source"] for c in cases).most_common()) + "\n",
         "## 1. 总体\n", "| 结果 | 带邮编 | 不带邮编 |", "|---|---|---|"]
    summary = {}
    for o in order:
        a = sum(1 for _, j, *_ in outcomes["带邮编"] if j == o)
        b = sum(1 for _, j, *_ in outcomes["不带邮编"] if j == o)
        summary[o] = {"with_postcode": a, "without_postcode": b}
        L.append(f"| {o} | {pct(a, len(cases))}（{a}） | {pct(b, len(cases))}（{b}） |")
    L.append("\n\"判 FIX\"指真实地址在参考库里却没找到（相当于误拒）；\"正确拒绝\"指参考库里没有这个新地址、校验器判 FIX。\n")

    L += ["## 2. 按真实写法特征（带邮编，参考库里有的地址）\n",
          "| 特征 | 条数 | 找对 | 其中直接通过 | 判 FIX | 错误建议 | 静默错误 |", "|---|---|---|---|---|---|---|"]
    groups = defaultdict(list)
    for c, j, *_ in outcomes["带邮编"]:
        if c["in_ref"]:
            for f in features(c):
                groups[f].append(j)
    for f, js in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(js) < 30:
            continue
        cnt = Counter(js)
        found = cnt["找对 · 直接通过"] + cnt["找对 · 要求确认"]
        L.append(f"| {f} | {len(js):,} | {pct(found, len(js))} | {pct(cnt['找对 · 直接通过'], len(js))} | "
                 f"{pct(cnt['判 FIX'], len(js))} | {pct(cnt['错误建议'], len(js))} | {pct(cnt['静默错误'], len(js))} |")

    L.append("\n## 3. 错误样例\n")
    for mode in ("带邮编", "不带邮编"):
        for o in ("静默错误", "错误建议", "判 FIX"):
            items = [x for x in outcomes[mode] if x[1] == o]
            if not items:
                continue
            L += [f"**{mode} · {o}**（{len(items)} 条，列出前 6 条）\n", "| 输入 | 结论 | 给出的地址 | 真实地址 |", "|---|---|---|---|"]
            for c, _, act, got, text in items[:6]:
                L.append(f"| {text.replace('|', '/')} | {act} | {got} | {c['truth_blk']} {c['truth_street']} {c['postcode']} |")
            L.append("")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "real_strings_eval.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (ROOT / "reports" / "real_strings_eval.json").write_text(json.dumps(
        {"n": len(cases), "in_reference": len(in_ref), "summary": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print("\n".join(L[:30]))


if __name__ == "__main__":
    main()
