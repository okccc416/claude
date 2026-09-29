"""本地 HTTP 服务：POST /v1/address:validate（请求结构对齐 Google AV），GET / 为演示页面。

启动：python -m avmvp.server [--port 8080] [--reference data/reference_sg.csv.gz]
仅依赖标准库 + rapidfuzz，便于在任何机器上演示。
"""

from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .reference import ReferenceDB
from .validator import Validator

ROOT = Path(__file__).resolve().parents[1]

DEMO_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>地址校验 MVP</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1b;--muted:#6b6b66;--line:#e4e4df;--ok:#1f7a4d;--warn:#a15c00;--bad:#b3261e}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--card:#1f1f1d;--ink:#ecece8;--muted:#a3a39c;--line:#33332f;--ok:#5fc48e;--warn:#e6a44a;--bad:#f07a72}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px}
h1{font-size:20px;margin:0 0 4px}.sub{color:var(--muted);margin:0 0 16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:14px}
.row{display:flex;gap:8px;flex-wrap:wrap}input,select,button{font:inherit;padding:9px 11px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink)}
input{flex:1;min-width:220px}button{cursor:pointer;background:var(--ink);color:var(--bg);border-color:var(--ink)}
.ex{margin-top:10px;display:flex;flex-wrap:wrap;gap:6px}.ex button{background:transparent;color:var(--muted);border-color:var(--line);font-size:13px;padding:4px 8px}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-weight:600;font-size:13px;border:1px solid currentColor}
.ACCEPT{color:var(--ok)}.CONFIRM,.CONFIRM_ADD_SUBPREMISES{color:var(--warn)}.FIX{color:var(--bad)}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:500}
.addr{font-size:17px;font-weight:600;margin:8px 0}.muted{color:var(--muted)}pre{white-space:pre-wrap;word-break:break-all;font-size:12px;color:var(--muted)}
</style></head><body><main>
<h1>新加坡地址校验 MVP</h1><p class="sub">输入任意写法的新加坡地址，返回结论、标准化地址、逐组件判断与原因码。</p>
<div class="card"><div class="row">
<input id="q" placeholder="例如：blk 10 bayfrnt ave s018956" value="10 Bayfrnt Avenue 018956">
<select id="s"><option>BALANCED</option><option>STRICT</option><option>LENIENT</option></select>
<button id="go">校验</button></div>
<div class="ex" id="ex"></div></div>
<div id="out"></div>
<script>
const EX=["10 Bayfront Avenue, Singapore 018956","018956 10 bayfront ave s'pore","10 Bayfrnt Avenue 018956","1 Raffles Place",
"10 Bayfront Avenue, Singapore 819643","999 Bayfront Avenue","Marina Bay Sands","Changi Airport Terminal 3","Tampines Avenue 7","34A Poxle Road",
"Attn: Jason Teo, Blk123 AMK Ave 6 # 05 - 12 S(560123) pls call b4 delivery 91234567, 请放门口"];
const ex=document.getElementById('ex');EX.forEach(t=>{const b=document.createElement('button');b.textContent=t;b.onclick=()=>{q.value=t;run()};ex.appendChild(b)});
const q=document.getElementById('q'),s=document.getElementById('s'),out=document.getElementById('out');
document.getElementById('go').onclick=run;q.addEventListener('keydown',e=>{if(e.key==='Enter')run()});
const esc=x=>String(x??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function run(){
 const r=await fetch('/v1/address:validate',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({address:{regionCode:'SG',addressLines:[q.value]},strictness:s.value})});
 const d=await r.json();const v=d.result.verdict,a=d.result.address;
 const comps=a.addressComponents.map(c=>`<tr><td>${esc(c.componentType)}</td><td>${esc(c.componentName.text)}</td><td>${esc(c.confirmationLevel)}</td><td class="muted">${[c.inferred&&'补全',c.replaced&&'替换',c.spellCorrected&&'纠错'].filter(Boolean).join(' / ')}${c.originalText?' ← '+esc(c.originalText):''}</td></tr>`).join('');
 const reasons=v.reasons.map(x=>`<li><code>${esc(x.code)}</code> ${esc(x.message)}</li>`).join('')||'<li class="muted">无</li>';
 const cands=(d.result.candidates||[]).map(c=>`<li>${esc(c.formattedAddress)}</li>`).join('');
 const NA={phones:'电话',emails:'邮箱',orderRefs:'订单号',recipients:'收件人',organizations:'公司',notes:'备注'};
 const info=Object.entries(d.result.nonAddressInfo||{}).map(([k,v])=>`<tr><td>${NA[k]||k}</td><td>${v.map(esc).join('<br>')}</td></tr>`).join('');
 out.innerHTML=`<div class="card"><span class="badge ${v.possibleNextAction}">${v.possibleNextAction}</span>
 <span class="muted"> 校验码 ${esc(v.verificationCode)} · 服务端耗时 ${esc(d.serverTimeMs)} ms</span>
 <div class="addr">${esc(a.formattedAddress||'—')}</div>
 <div class="muted">输入粒度 ${v.inputGranularity} → 校验粒度 ${v.validationGranularity}（纠错前 ${v.preCorrectionGranularity}）</div></div>
 <div class="card"><b>原因码</b><ul>${reasons}</ul>${cands?`<b>候选地址</b><ul>${cands}</ul>`:''}</div>
 ${info?`<div class="card"><b>已分离的非地址信息</b><table>${info}</table></div>`:''}
 <div class="card"><b>逐组件判断</b><table><tr><th>组件</th><th>值</th><th>确认级别</th><th>处理</th></tr>${comps}</table></div>
 <div class="card"><details><summary>原始 JSON</summary><pre>${esc(JSON.stringify(d,null,2))}</pre></details></div>`;
}
run();
</script></main></body></html>"""


def make_handler(validator: Validator):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            if self.path in ("/", "/index.html"):
                self._send(200, DEMO_HTML.encode(), "text/html; charset=utf-8")
            elif self.path == "/healthz":
                self._send(200, b'{"status":"ok"}', "application/json")
            else:
                self._send(404, b'{"error":"not found"}', "application/json")

        def do_POST(self):  # noqa: N802
            if self.path != "/v1/address:validate":
                return self._send(404, b'{"error":"not found"}', "application/json")
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                address = body.get("address") or {}
                text = body.get("text") or ", ".join(
                    [*address.get("addressLines", []), address.get("postalCode", "")]).strip(", ")
                strictness = (body.get("strictness") or "BALANCED").upper()
                if not text or strictness not in ("STRICT", "BALANCED", "LENIENT"):
                    raise ValueError("需要 address.addressLines（或 text），strictness 取 STRICT/BALANCED/LENIENT")
            except (ValueError, json.JSONDecodeError) as e:
                return self._send(400, json.dumps({"error": str(e)}, ensure_ascii=False).encode(), "application/json")
            t = time.perf_counter()
            res = validator.validate(text, strictness=strictness)
            out = validator.to_response(res)
            out["serverTimeMs"] = round((time.perf_counter() - t) * 1000, 2)
            self._send(200, json.dumps(out, ensure_ascii=False).encode(), "application/json; charset=utf-8")

        def log_message(self, fmt, *args):
            pass

    return Handler


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--reference", default=str(ROOT / "data" / "reference_sg.csv.gz"))
    ap.add_argument("--attributes", help="可选：楼栋属性 CSV（postal,max_floor）")
    args = ap.parse_args()
    t = time.time()
    db = ReferenceDB.load(args.reference)
    if args.attributes:
        db.load_building_attributes(args.attributes)
    print(f"参考库已加载：{len(db.entities):,} 个地址实体（{time.time() - t:.1f}s）")
    server = ThreadingHTTPServer((args.host, args.port), make_handler(Validator(db)))
    print(f"演示页面：http://{args.host}:{args.port}/    接口：POST /v1/address:validate")
    server.serve_forever()


if __name__ == "__main__":
    main()
