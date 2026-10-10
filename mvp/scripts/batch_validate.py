"""批量清洗：读入一个 CSV（每行一个地址），逐行校验，在原表后面追加结论、标准化地址、坐标、原因码和候选。

适用于主数据清洗、历史订单回扫这类离线场景（Loqate 式批量；Google AV 没有原生批量接口）。

  python scripts/batch_validate.py input.csv output.csv --region AE --column address
  python scripts/batch_validate.py input.csv output.csv --region-column country --column address
  可选：--intl-llm data/models/xxx.gguf（离线批量可以接受本地小模型的延迟）

输出新增的列：
  av_action           ACCEPT / CONFIRM / FIX（与 Google 一致，CONFIRM_ADD_SUBPREMISES 只用于美国地址）
  av_granularity      验证到哪一级：SUB_PREMISE / PREMISE / BLOCK（日本）/ ROUTE / OTHER
  av_geocode_granularity  坐标精度：PREMISE / PREMISE_PROXIMITY / BLOCK / ROUTE / OTHER
  av_complete         地址是否完整（Google 的 addressComplete：没有缺失字段、没有未识别的词）
  av_missing          缺的字段（Google 的 missingComponentTypes，| 分隔）
  av_address          标准化地址
  av_lat, av_lng      坐标
  av_reasons          原因码（| 分隔）
  av_candidates       候选地址（结论不是 ACCEPT 时，最多 3 个，| 分隔）
  av_error            这一行出错时的说明
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp.intl.markets import MARKETS  # noqa: E402
from avmvp.router import MarketRouter  # noqa: E402

OUT_COLS = ["av_action", "av_granularity", "av_geocode_granularity", "av_complete", "av_missing", "av_address",
            "av_lat", "av_lng", "av_reasons", "av_candidates", "av_error"]


def flatten(resp: dict) -> dict:
    """一条响应 -> 追加的列（字段含义同 Google AV：验证到哪一级、坐标精度、地址是否完整、缺哪些字段）。"""
    r = resp["result"]
    v, a = r["verdict"], r["address"]
    loc = (r.get("geocode") or {}).get("location") or {}
    return {"av_action": v["possibleNextAction"], "av_granularity": v["validationGranularity"],
            "av_geocode_granularity": v.get("geocodeGranularity", ""), "av_complete": v.get("addressComplete", ""),
            "av_missing": "|".join(a.get("missingComponentTypes") or []),
            "av_address": a["formattedAddress"], "av_lat": loc.get("latitude", ""),
            "av_lng": loc.get("longitude", ""), "av_reasons": "|".join(x["code"] for x in v["reasons"]),
            "av_candidates": "|".join(c["formattedAddress"] for c in (r.get("candidates") or [])[:3]),
            "av_error": ""}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--column", default="address", help="地址所在的列")
    ap.add_argument("--region", help="所有行都是同一个国家 / 地区（如 AE）")
    ap.add_argument("--region-column", help="或者：国家 / 地区代码所在的列")
    ap.add_argument("--strictness", default="BALANCED", choices=["STRICT", "BALANCED", "LENIENT"])
    ap.add_argument("--parser", default="hybrid", choices=["rules", "crf", "hybrid"])
    ap.add_argument("--intl-llm", help="可选：本地小模型 GGUF 文件（多市场引擎的级联兜底）")
    args = ap.parse_args()
    if not args.region and not args.region_column:
        ap.error("需要 --region 或 --region-column")

    llm = None
    if args.intl_llm:
        from avmvp.intl.llm import LlamaCppLLM
        llm = LlamaCppLLM(args.intl_llm)
    sg = None
    if (ROOT / "data" / "reference_sg_2026.csv.gz").exists() or (ROOT / "data" / "reference_sg.csv.gz").exists():
        from avmvp import ReferenceDB, Validator

        ref = ROOT / "data" / ("reference_sg_2026.csv.gz" if (ROOT / "data" / "reference_sg_2026.csv.gz").exists()
                               else "reference_sg.csv.gz")
        sg = lambda: Validator(ReferenceDB.load(ref))  # noqa: E731
    router = MarketRouter(sg, ["SG", *MARKETS], args.parser, log=lambda *_: None, llm=llm)

    with open(args.input, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        cols = list(reader.fieldnames or [])
    if args.column not in cols:
        sys.exit(f"找不到地址列 {args.column!r}（有：{', '.join(cols)}）")
    t = time.time()
    stats: Counter = Counter()
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols + [c for c in OUT_COLS if c not in cols])
        w.writeheader()
        for i, row in enumerate(rows, 1):
            region = (args.region or row.get(args.region_column) or "").strip().upper()
            text = (row.get(args.column) or "").strip()
            try:
                if not text:
                    raise ValueError("地址为空")
                out = flatten(router.validate(region, text, args.strictness))
            except ValueError as e:  # 不支持的国家、空地址等：记录原因，继续下一行
                out = {c: "" for c in OUT_COLS} | {"av_error": str(e)}
            stats[out["av_action"] or "ERROR"] += 1
            w.writerow(row | out)
            if i % 500 == 0:
                print(f"  {i:,}/{len(rows):,}（{time.time() - t:.0f}s）", flush=True)
    n = max(len(rows), 1)
    print(f"完成 {len(rows):,} 行，{time.time() - t:.1f}s -> {args.output}")
    print("  " + "  ".join(f"{k} {v:,}（{100 * v / n:.1f}%）" for k, v in stats.most_common()))


if __name__ == "__main__":
    main()
