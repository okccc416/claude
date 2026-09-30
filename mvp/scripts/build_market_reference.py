"""构建各市场参考库（道路、片区、POI、邮编、A 类官方地址点）-> data/markets/{国家代码}/reference.{pkl,sqlite}

  python scripts/build_market_reference.py [--markets AU,DE,...]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp.intl.markets import MARKETS  # noqa: E402
from avmvp.intl.reference import build  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", default=",".join(MARKETS))
    args = ap.parse_args()
    for code in args.markets.split(","):
        t = time.time()
        print(f"{code} {MARKETS[code].name}", flush=True)
        build(code, MARKETS[code].cls, log=lambda s: print(s, flush=True))
        print(f"  完成（{time.time() - t:.0f}s）", flush=True)


if __name__ == "__main__":
    main()
