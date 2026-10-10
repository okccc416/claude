"""竞品地理编码对比：把评测集的查询逐条发给竞品接口，原样保存返回，供 geo_real_eval.py --competitor 评测。

只用于评测打分，不用竞品的返回改进本方案（使用前确认竞品平台的服务条款允许这类对比测试）。
key 从环境变量 COMP_AK 读取，不写进代码、不提交；应用开了 SN 签名校验（百度返回 status 211）时，
再设 COMP_SK（应用的 Secret Key），脚本按百度的规则算 sn 签名。默认是百度地图地理编码接口（返回 GCJ-02 坐标，
海外 GCJ-02 与 WGS-84 相同）；--endpoint 可换成别的接口，{address} 和 {ak} 会被替换。

  COMP_AK=... python scripts/competitor_geocode.py --cases final_effective_full_responses_851.jsonl \\
      --out competitor_responses.jsonl [--sleep 0.3]
已写过的 case 会跳过，可以断点续跑。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT = "https://api.map.baidu.com/geocoding/v3/?address={address}&output=json&ret_coordtype=gcj02ll&ak={ak}"
SAFE = "/:=&?#+!$,;'@()*[]"


def build_url(template: str, address: str, ak: str, sk: str) -> str:
    """请求地址。有 SK 时按百度 SN 规则：未转码的"路径?参数"整体转码一次、末尾接 SK，quote_plus 后取 MD5 作 sn，
    最终地址是同一串原始参数加 sn 再整体转码（不能先转码地址再签名，否则两边算出的串不一致）。
    转码时保留的字符里有 # & =，所以地址里的这几个字符先换掉（Calle 16 #22-53 -> Calle 16 No. 22-53）。"""
    if not sk:
        return template.format(address=urllib.parse.quote(address), ak=ak)
    address = address.replace("#", " No. ").replace("&", " y ").replace("=", " ")
    parts = urllib.parse.urlsplit(template)
    raw = f"{parts.path}?{parts.query}".format(address=address, ak=ak)
    sn = hashlib.md5(urllib.parse.quote_plus(urllib.parse.quote(raw, safe=SAFE) + sk).encode("utf-8")).hexdigest()
    return urllib.parse.quote(f"{parts.scheme}://{parts.netloc}{raw}&sn={sn}", safe=SAFE)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True, help="每行一个 JSON，含 case_id 和 query")
    ap.add_argument("--out", required=True)
    ap.add_argument("--endpoint", default=DEFAULT)
    ap.add_argument("--sleep", type=float, default=0.3)
    args = ap.parse_args()
    ak = os.environ.get("COMP_AK")
    if not ak:
        sys.exit("需要环境变量 COMP_AK")
    sk = os.environ.get("COMP_SK", "")
    done = set()
    out = Path(args.out)
    if out.exists():
        done = {json.loads(x)["case_id"] for x in out.open(encoding="utf-8")}
    cases = [json.loads(x) for x in open(args.cases, encoding="utf-8")]
    with out.open("a", encoding="utf-8") as f:
        for i, c in enumerate(cases):
            if c["case_id"] in done:
                continue
            url = build_url(args.endpoint, c["query"], ak, sk)
            body, err = "", ""
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(url, timeout=20) as r:
                        body = r.read().decode("utf-8", "replace")
                    break
                except Exception as e:  # noqa: BLE001  网络抖动：退避重试
                    err = str(e)
                    time.sleep(2 ** (attempt + 1))
            f.write(json.dumps({"case_id": c["case_id"], "query": c["query"], "response": body, "error": err},
                               ensure_ascii=False) + "\n")
            f.flush()
            if (i + 1) % 50 == 0:
                print(i + 1, flush=True)
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
