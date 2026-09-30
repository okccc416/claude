"""新加坡引擎迭代用的开发集检查（只用开发数据，测试集留到最后只跑一次）。

  - 标准变形开发集 golden_dev、噪声开发集 noisy_dev（2017 参考库）
  - 模拟订单的训练部分（orders_sg_v1.csv 中 split=train，2017 参考库）
  - 调研测试集的开发版（另一随机种子生成的 data/research_dev_sg.csv，2026 参考库）
  - 真实商户地址的开发样本（与 8,000 条测试样本不重叠的另外 8,000 条，2026 参考库）

  python scripts/sg_dev_check.py
"""

from __future__ import annotations

import csv
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from avmvp import ReferenceDB, Validator  # noqa: E402
from avmvp.normalize import match_key  # noqa: E402
from avmvp.validator import ACCEPT, ADD_SUB, CONFIRM  # noqa: E402
import evaluate_labeled as el  # noqa: E402
import evaluate_real_strings as er  # noqa: E402
from evaluate import load_golden, metrics  # noqa: E402
from evaluate_noisy import load as load_noisy  # noqa: E402
from evaluate_noisy import summarize  # noqa: E402
from whatif_current_reference import judge  # noqa: E402


def pct(x):
    return f"{100 * x:.1f}%"


def main() -> None:
    t0 = time.time()
    db17 = ReferenceDB.load(ROOT / "data" / "reference_sg.csv.gz")
    db26 = ReferenceDB.load(ROOT / "data" / "reference_sg_2026.csv.gz")
    v17, v26 = Validator(db17), Validator(db26)
    out = []

    rows = load_golden("dev")
    preds = [((ACCEPT if r.action == ADD_SUB else r.action), r.entity.eid if r.entity else None)
             for r in (v17.validate(x["input"]) for x in rows)]
    m = metrics(rows, preds)
    out.append(f"标准变形 dev：完全正确 {pct(m['full_correct'])}  误收 {pct(m['FAR'])}  误拒 {pct(m['FRR'])}  "
               f"静默 {pct(m['silent_wrong'])}")
    rows = load_noisy("dev")
    preds = [((ACCEPT if r.action == ADD_SUB else r.action), r.entity.eid if r.entity else None)
             for r in (v17.validate(x["input"]) for x in rows)]
    m = summarize("dev", rows, preds)
    out.append(f"噪声 dev：地址识别 {pct(m['addr_found'])}  直接通过 {pct(m['clean_accept'])}  "
               f"静默 {pct(m['silent_wrong'])}")

    rows = [r for r in el.load(ROOT / "labeled" / "orders_sg_v1.csv", db17) if r["split"] == "train"]
    oc = Counter(el.outcome(r, v17.validate(r["input"])) for r in rows)
    out.append("模拟订单 train：" + "  ".join(f"{k} {pct(oc[k] / len(rows))}" for k in el.OUTCOMES))

    with open(ROOT / "data" / "research_dev_sg.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    oc = Counter()
    for r in rows:
        truth = (r["truth_blk"], match_key(r["truth_street"]), r["truth_postal"]) if r["truth_blk"] else None
        oc[judge(v26.validate(r["input"]), truth)] += 1
    out.append("调研 dev（2026 库）：" + "  ".join(f"{k} {pct(v / len(rows))}" for k, v in sorted(oc.items())))

    cases = er.build_cases(8000, 20261102, offset=8000)
    oc = Counter()
    for c in cases:
        key = (c["truth_blk"], match_key(c["truth_street"]), c["postcode"])
        oc[er.judge(v26.validate(f"{c['freeform']}, Singapore {c['postcode']}"), key, True)] += 1
    out.append("真实地址 dev（2026 库）：" + "  ".join(f"{k} {pct(v / len(cases))}" for k, v in sorted(oc.items())))
    print("\n".join(out))
    print(f"（{time.time() - t0:.0f}s）")


if __name__ == "__main__":
    main()
