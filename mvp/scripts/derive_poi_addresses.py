"""刷新各市场的商户地址门牌点（不重建整个参考库）。

  python scripts/derive_poi_addresses.py [--markets AU,...]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avmvp.intl.markets import MARKETS  # noqa: E402
from avmvp.intl.poiaddr import derive  # noqa: E402
from avmvp.intl.reference import MarketReference  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", default=",".join(MARKETS))
    args = ap.parse_args()
    for code in args.markets.split(","):
        t = time.time()
        ref = MarketReference.load(code)
        print(code, MARKETS[code].name, flush=True)
        derive(ref, log=lambda s: print(s, flush=True))
        ref.save()
        print(f"  完成（{time.time() - t:.0f}s）", flush=True)


if __name__ == "__main__":
    main()
