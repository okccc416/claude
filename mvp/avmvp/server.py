"""本地 HTTP 服务：POST /v1/address:validate（请求结构对齐 Google AV）、POST /v1/address:batchValidate（批量），
GET /v1/markets 市场列表，GET / 演示页面。接口说明见 docs/openapi.yaml。

按请求里的 address.regionCode 分给对应市场的引擎（见 router.py）：SG 用新加坡专用引擎，
AU / DE / FR / NL / AE / SA / MY / ID / TH / VN / PH 用多市场引擎。

启动：python -m avmvp.server [--port 8080] [--markets SG,AU,...] [--parser hybrid] [--preload]
"""

from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from .intl.markets import MARKETS
from .reference import ReferenceDB
from .router import MarketRouter
from .validator import Validator

ROOT = Path(__file__).resolve().parents[1]

DEMO_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>地址校验</title>
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
.mk{font-size:13px;color:var(--muted);margin-top:8px}
</style></head><body><main>
<h1>地址校验</h1><p class="sub">选择国家 / 地区，输入任意写法的地址，返回结论、标准化地址、逐组件判断、坐标与原因码。</p>
<div class="card"><div class="row">
<select id="m"></select>
<input id="q" placeholder="输入地址">
<select id="s"><option>BALANCED</option><option>STRICT</option><option>LENIENT</option></select>
<button id="go">校验</button></div>
<div class="mk" id="mk"></div>
<div class="ex" id="ex"></div></div>
<div id="out"></div>
<script>
const EXAMPLES=__EXAMPLES__;
const CLS={A:'A 类：官方地址表，逐门牌验真',B:'B 类（中东）：道路 / 楼宇 / 片区验真，门牌号无法证实',C:'C 类（没有开放地址表）：道路 / 楼宇 / 片区验真，门牌号无法证实'};
const $=id=>document.getElementById(id);const q=$('q'),s=$('s'),m=$('m'),out=$('out'),ex=$('ex');
const esc=x=>String(x??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let MK=[];
async function init(){
 MK=(await (await fetch('/v1/markets')).json()).markets;
 m.innerHTML=MK.map(x=>`<option value="${x.code}" ${x.available?'':'disabled'}>${esc(x.name)}（${x.code}）${x.available?'':' · 未构建'}</option>`).join('');
 m.onchange=()=>{pick();q.value=(EXAMPLES[m.value]||[''])[0];run()};pick();q.value=(EXAMPLES[m.value]||[''])[0];run();
}
function pick(){const x=MK.find(y=>y.code===m.value)||{};
 $('mk').textContent=`${CLS[x.cls]||''} · 覆盖：${(x.cities||[]).join('、')}`;
 ex.innerHTML='';(EXAMPLES[m.value]||[]).forEach(t=>{const b=document.createElement('button');b.textContent=t;b.onclick=()=>{q.value=t;run()};ex.appendChild(b)});}
$('go').onclick=run;q.addEventListener('keydown',e=>{if(e.key==='Enter')run()});
async function run(){
 if(!q.value.trim())return;out.innerHTML='<div class="card muted">校验中（首次使用某个市场需要加载参考数据）…</div>';
 const r=await fetch('/v1/address:validate',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({address:{regionCode:m.value,addressLines:[q.value]},strictness:s.value})});
 const d=await r.json();if(!r.ok){out.innerHTML=`<div class="card FIX">${esc(d.error)}</div>`;return}
 const v=d.result.verdict,a=d.result.address,md=d.result.metadata||{};
 const comps=a.addressComponents.map(c=>`<tr><td>${esc(c.componentType)}</td><td>${esc(c.componentName.text)}</td><td>${esc(c.confirmationLevel)}</td><td class="muted">${[c.inferred&&'补全',c.replaced&&'替换',c.spellCorrected&&'纠错'].filter(Boolean).join(' / ')}${c.originalText?' ← '+esc(c.originalText):''}</td></tr>`).join('');
 const reasons=v.reasons.map(x=>`<li><code>${esc(x.code)}</code> ${esc(x.message)}</li>`).join('')||'<li class="muted">无</li>';
 const cands=(d.result.candidates||[]).map(c=>`<li>${esc(c.formattedAddress)}</li>`).join('');
 const NA={phones:'电话',emails:'邮箱',urls:'网址',orderRefs:'订单号',recipients:'收件人',organizations:'公司',notes:'备注'};
 const info=Object.entries(d.result.nonAddressInfo||{}).map(([k,v])=>`<tr><td>${NA[k]||k}</td><td>${v.map(esc).join('<br>')}</td></tr>`).join('');
 const codes=Object.entries(d.result.codes||{}).map(([k,v])=>`<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join('');
 const g=d.result.geocode&&d.result.geocode.location;
 out.innerHTML=`<div class="card"><span class="badge ${v.possibleNextAction}">${v.possibleNextAction}</span>
 <span class="muted"> ${v.confidence!=null?`置信度 ${(v.confidence*100).toFixed(2)}% · `:''}${v.verificationCode?'校验码 '+esc(v.verificationCode)+' · ':''}解析 ${esc(md.parser||'')} · 服务端耗时 ${esc(d.serverTimeMs)} ms</span>
 <div class="addr">${esc(a.formattedAddress||'—')}</div>
 <div class="muted">校验粒度 ${esc(v.validationGranularity)}${g?` · 坐标 ${g.latitude.toFixed(5)}, ${g.longitude.toFixed(5)}`:''}</div></div>
 <div class="card"><b>原因码</b><ul>${reasons}</ul>${cands?`<b>候选地址</b><ul>${cands}</ul>`:''}</div>
 ${info?`<div class="card"><b>已分离的非地址信息</b><table>${info}</table></div>`:''}
 ${codes?`<div class="card"><b>识别出的地址编码</b><table>${codes}</table></div>`:''}
 <div class="card"><b>逐组件判断</b><table><tr><th>组件</th><th>值</th><th>确认级别</th><th>处理</th></tr>${comps}</table></div>
 <div class="card"><details><summary>原始 JSON</summary><pre>${esc(JSON.stringify(d,null,2))}</pre></details></div>`;
}
init();
</script></main></body></html>"""

# 演示页面的示例输入（各市场取自开发集里真实商户自填的地址；第一条为默认示例）
EXAMPLES = {
    "SG": ["10 Bayfront Avenue, Singapore 018956", "018956 10 bayfront ave s'pore", "10 Bayfrnt Avenue 018956",
           "10 Bayfront Avenue, Singapore 819643", "999 Bayfront Avenue", "Marina Bay Sands", "Tampines Avenue 7",
           "Attn: Jason Teo, Blk123 AMK Ave 6 # 05 - 12 S(560123) pls call b4 delivery 91234567, 请放门口"],
    "AU": ["360 Lonsdale Street, Melbourne, 3000", "636 Inkerman Rd, Melbourne, 3161",
           "203-205 Blackburn Rd, Melbourne, 3149", "24 Salicki Ave, Epping, 3076", "Granville, Sydney, 2142"],
    "DE": ["Invalidenstraße 117, Berlin, 10115", "Lankwitzer Str. 14, 12107 Berlin", "Müllerstraße 15, Berlin, 13347",
           "Invalidenstraße 999, 10115 Berlin"],
    "FR": ["67 Rue Galande, Paris, 75005", "13 rue Brey, Paris", "10 Cr Louis Lumière, Vincennes, 94300"],
    "NL": ["Sint Antoniesbreestraat 51, Amsterdam, 1011 HB", "Stadhouderskade 101, 1073 AW Amsterdam",
           "Lutmastraat 180, Amsterdam, 1073 RE", "Amsterdamse Bos, Amstelveen"],
    "AE": ["Burlington Tower - 16th & 17th Floor Marasi Dr, دبي", "Latifa Tower - Shop No.L2, Ground Floor - Sheikh Zayed Rd, Dubai",
           "Naif Road, Naif, Deira Souq, Opposite Al Futtaim Mosque, Dubai", "Ground Floor, Mirdif City Centre, Dubai"],
    "SA": ["PRX9+WV5, Riyadh, 14232", "RM58+685, طريق الثمامة, الرياض",
           "Shop# 302, Ground Floor, Gulf Commercial Centre, الرياض, 12642", "حي بدر, الرياض, 14724"],
    "MY": ["35 Jalan AWF 2, Ampang, 68000", "G-38, Casa Tiara, Jalan SS 16/1, Subang Jaya, 47500",
           "Jalan Genting Kelang, Jln Taman Ibu Kota, Setapak, 53300", "SELAYANG, Batu, 68100"],
    "ID": ["Jl. Cideng Timur No.16A, RT.1/RW.4, Jakarta Pusat, 10130", "Jalan Letjen Suprapto 32, Jakarta, 10640",
           "Jl. KH. Mas Mansyur, RT.007/RW.003, Tangerang Kota, 15145", "Chedoya St, Jakarta Barat, 11520"],
    "TH": ["824 ถนน สุขุมวิท, คลองเตย, 10110", "1 Phatthanakan Rd, กรุงเทพมหานคร, 10250",
           "2409 Phetchaburi Rd, กรุงเทพมหานคร, 10310", "59 กลาง 1 Suphaphong Alley, กรุงเทพมหานคร, 10250"],
    "VN": ["226 Đường Trần Văn Kiểu, Quận 6, 73115", "42/5 Hẻm 42 Lương Thế Vinh, Quận Tân Phú, 72015",
           "42 Lê Lợi, P. Bến Nghế, Quận 1, TP. HCM", "31031983 hcmc, Quận Gò Vấp"],
    "PH": ["55-51, Angelo St, Quezon City, 1403", "Jiao Building, Timog Ave, Quezon City, 1100",
           "M. H. Del Pilar St 223, Malabon, 1474", "14.515182,121.003079, Parañaque, 1300"],
    # Google Address Validation 覆盖的其他国家 / 地区（取自开发集里商户自填的地址，另加几条演示写法）
    "CA": ["20 Camden St Suite 200, Toronto, M5V 1V1", "531 Yonge St, Toronto, M4Y 1Y5", "1500 – 5255 Yonge Street, Toronto, M2N 6P4", "Sherbourne St N, Toronto, M4W 2T2"],
    "MX": ["Av. Ejército Nacional Mexicano 205 Col, Miguel Hidalgo, 11300", "14 de Agosto 29, Naucalpan de Juárez, 53910", "Parque arboledas, Enrique Pestalozzi, Benito Juárez, 03100", "Chihuahua 222, Ciudad de México, 06700"],
    "PR": ["6471 Av. Isla Verde, Carolina, 00979", "175 C. O'Neill, San Juan, 00918", "90 C. Alondra Ofi 28, San Juan, 00983", "Isla Verde, Carolina, 00979"],
    "BR": ["Avenida Susana, 262, São Paulo, 04130-000", "Rua Emília Marengo, 306, São Paulo, 03336-000", "Rua Luís Toschi, 93, São Paulo, 05343-020", "AVENIDA ELISEU DE ALMEIDA, São Paulo, 05145-907"],
    "AR": ["Nazarre 3772, Ciudad de Buenos Aires, C1417", "Homero 1944, Ciudad de Buenos Aires, C1407", "Tucumán 971, Ciudad de Buenos Aires, C1049AAS", "Freire 1319, Ciudad de Buenos Aires, C1426ELR"],
    "CL": ["Calle José Toribio Medina 19, Santiago, 8320000", "Av. Manquehue Nte. 1270, Vitacura, 7650705", "Avenida José Miguel Carrera 8193, La Cisterna", "Av. Francisco Bilbao, Las Condes"],
    "CO": ["Calle 11 15-36, Bogotá, D.C., 111411", "Carrera 9 2-60, Bogotá, D.C., 110321", "Cl. 69 #11a-34, Bogotá, D.C., 110231", "Cra. 7 # 31-10, Bogotá, D.C."],
    "GB": ["12 Camley Street, London, N1C 4PW", "36 Duke Of York Square, London, SW3 4LY", "228 Graham Road, Hackney, E8 1BP", "17 Leicester Sq, London"],
    "IE": ["35 Molesworth Street, Dublin, D02 A023", "Carriglea Gardens, 8 Kill Avenue, Dun Laoghaire, A96 A593", "Unit 6, Glenview Industrial Estate, Herberton Rd, Dublin, D12 PE8C", "East Essex street, Temple Bar, Dublin"],
    "BE": ["Avenue Jules du Jardin 7, Woluwé-Saint-Pierre, 1150", "Rue Simonis 46, Ixelles, 1050", "Louizalaan 43 Avenue Louise, Elsene, 1050", "Ninoofsesteenweg, Anderlecht, 1070"],
    "LU": ["54 Bd Grande-Duchesse Charlotte, Luxembourg, 1330", "9 Avenue du Blues, Sanem, 4368", "11-13 Rte de Mondorf, Frisange, 3337", "65 zone industrielle Gadderscheier, Differdange, 4984"],
    "CH": ["Wagistrasse 21, Schlieren, 8952", "Depotweg 3-5, Zürich, 8048", "Altstetterstrasse 159, Zuerich, 8048", "Quartierverein Wipkingen Postfach 8037 Zürich, Zürich, 8037"],
    "AT": ["Brunnengasse 75, Wien, 1160", "Walter-Berry-Weg 3, Wien, 1190", "Naschmarkt 1, Wien, 1060", "Braunhubergasse 21/6/G2, Wien, 1110"],
    "IT": ["VIALE CERTOSA 46, MILAN, 20155", "CORSO SEMPIONE 67, MILANO, 20149", "Via Ampere, Milano", "Via Rossini 6/8, Milano"],
    "ES": ["C. Velilla, 7, Madrid, 28032", "Calle de la Esmeralda, 14, Madrid, 28026", "Calle Grecia, Pozuelo De Alarcón, 28224", "C/ Serrano, Madrid, 28006"],
    "PT": ["Rua Padre Francisco Álvares 1, Lisboa, 1500-476", "Rua Azedo Gneco, Nº 74, Lisboa, 1350-039", "Av. Conde Valbom 84a, Lisboa, 1050-069", "C. C. Colombo, Lj A003, Benfica, 1500-392"],
    "DK": ["Høffdingsvej 32-36, København, 2500", "NORDRE FRIHAVNSGADE 36, KØBENHAVN, 2100", "Noerre Voldgade 90, Copenhagen, 1358", "C.M. LARSENS ALLÉ, COPENHAGEN, 2770"],
    "SE": ["Stora Gungans väg 14, Stockholm, 122 31", "Arenavägen 41, Johanneshov, 121 77", "Källängsvägen 65, Lidingö, 181 44", "Ösby stationshus, Stocksund, 182 64"],
    "NO": ["Hovfaret 13, Oslo, 0275", "Teglverksgata 9A, Oslo, 0553", "Møllergata 34, Oslo, 0179", "Apotekergata, Apotekergata, 0180"],
    "FI": ["Yrjönkatu 31, Helsinki, 00100", "Eerikinkatu 20 A 10, Helsinki, 00100", "7 Sörnäisten rantatie, Helsinki, 00530", "Ranckenintie, Helsinki, 00920"],
    "EE": ["Viru väljak 4-6, 10111 Tallinn, Estonia, Tallinn, 10111", "Rotermanni tn 18/1, Tallinn, 10111", "Laki tn 30B, Tallinn, 12915", "Sadama 25, Tallinn, 10111"],
    "LV": ["Kazdangas iela 21, Rīga, 1004", "Hanzas iela 16, Rīga, 1045", "Braslas iela 29, Rīga, 1084", "Lidostas parks, Mārupe, LV-2167"],
    "LT": ["Pavilnionių g. 65, Vilnius, LT-06257", "Markučių g. 34, Vilnius, 11347", "Jurgio Dobkevičiaus gatvė 8, Vilnius, 02189", "Eitminų g., Vilnius, 12131"],
    "PL": ["Obozowa 63/65, Warszawa, 01-418", "ul. Białobrzeska 8 /10, Warszawa, 02-380", "Wilcza 29a/lok 7, Warszawa, 00-544", "Burakowska 16a/lok. 79, Warszawa, 01-066"],
    "CZ": ["Školská 687/13, Praha, 110 00", "Neklanova 120/18, Praha 2, 128 00", "Peroutkova 18, Praha, 158 00", "Vodičkova 38, Praha 1"],
    "SK": ["Bottova 7939/2a, Bratislava, 811 09", "Metodova 17904/6, Bratislava, 821 08", "Smrečianska 3599/20, Bratislava, 811 05", "Seberíniho 821 01, Bratislava, 821 03"],
    "HU": ["Kondorosi út 3., Budapest 1116, Budapest, 1116", "Szent István körút 18, Budapest, 1136", "Duna utca 1, Budapest, 1221", "ÓRIÁSBUBORÉK, Budapest, 1028"],
    "SI": ["Celovška 91, Ljubljana, 1000", "Slovenska cesta 34, Ljubljana, 1000", "Šmartinska cesta 152, Ljubljana, 1000", "Pod gradom 1, Slovenj Gradec, 2380"],
    "HR": ["Krčka ul. 3, Zagreb, 10000", "Palmotićeva ul. 29, Zagreb, 10000", "Maksimirsko naselje IV 27, Zagreb, 10000", "Ilica 999, Zagreb"],
    "BG": ["ul. Elisaveta Bagryana 14, София, 1111", "Булевард Стефан Стамболов 6, София, 1000", "жк.Сухата река, бл.102А вх.А, София, 1517", "pl. Petko R. Slaveykov 11, София, 1000"],
    "NZ": ["25 Andromeda Cres, Auckland, 2013", "591a Remuera Rd, Auckland, 1050", "450 Mount Eden Rd, Auckland, 1024", "Mt Albert, Auckland, 1025"],
    "JP": ["東京都渋谷区神南1丁目12-13", "1 Chome-24-15 Shibuya, Shibuya City, Tokyo 150-0002", "富ヶ谷1丁目10-8, 渋谷区, 151-0063", "丸の内2-99-1, 千代田区"],
    "IN": ["Jeevan Bharat, 302 A, 17th Rd, near Khar Gymkhana, Mumbai, 400052", "256 Abdul Rehman Street, Mandvi, Mumbai, 400003", "Hill Rd, Mumbai, 400050", "2E Sane Guruji Road, Mumbai, 400034"],
}


def make_handler(router: MarketRouter):
    page = DEMO_HTML.replace("__EXAMPLES__", json.dumps(EXAMPLES, ensure_ascii=False)).encode()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str = "application/json; charset=utf-8") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode())

        def do_GET(self):  # noqa: N802
            if self.path in ("/", "/index.html"):
                self._send(200, page, "text/html; charset=utf-8")
            elif self.path == "/healthz":
                self._json(200, {"status": "ok"})
            elif self.path == "/v1/markets":
                self._json(200, {"markets": router.describe()})
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):  # noqa: N802
            if self.path not in ("/v1/address:validate", "/v1/address:batchValidate"):
                return self._json(404, {"error": "not found"})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            except (ValueError, json.JSONDecodeError) as e:
                return self._json(400, {"error": f"请求体不是合法 JSON：{e}"})
            if self.path == "/v1/address:validate":
                try:
                    out = validate_one(router, body)
                except ValueError as e:  # UnsupportedRegion 也是 ValueError
                    return self._json(400, {"error": str(e)})
                return self._json(200, out)
            # 批量：{"requests": [与单条相同的请求体, ...]}，最多 MAX_BATCH 条；单条出错不影响其他条
            reqs = body.get("requests")
            if not isinstance(reqs, list) or not reqs or len(reqs) > MAX_BATCH:
                return self._json(400, {"error": f"需要 requests 数组，1–{MAX_BATCH} 条"})
            t = time.perf_counter()
            responses = []
            for r in reqs:
                try:
                    responses.append(validate_one(router, r if isinstance(r, dict) else {}))
                except ValueError as e:
                    responses.append({"error": str(e)})
            self._json(200, {"responses": responses, "serverTimeMs": round((time.perf_counter() - t) * 1000, 2)})

        def log_message(self, fmt, *args):
            pass

    return Handler


MAX_BATCH = 1000


def request_threshold(body: dict) -> float | None:
    v = body.get("confidenceThreshold")
    if v is None:
        return None
    if not isinstance(v, (int, float)) or not 0 <= v <= 1:
        raise ValueError("confidenceThreshold 取 0–1 之间的数")
    return float(v)


def request_text(body: dict) -> tuple[str, str, str]:
    """请求体（与 Google AV 相同）-> (国家 / 地区代码, 地址文字, 严格度)。"""
    address = body.get("address") or {}
    text = body.get("text") or ", ".join(x for x in [
        *address.get("addressLines", []), address.get("locality", ""),
        address.get("administrativeArea", ""), address.get("postalCode", "")] if x).strip(", ")
    region = (address.get("regionCode") or body.get("regionCode") or "SG").upper()
    strictness = (body.get("strictness") or "BALANCED").upper()
    if not text or strictness not in ("STRICT", "BALANCED", "LENIENT"):
        raise ValueError("需要 address.addressLines（或 text），strictness 取 STRICT/BALANCED/LENIENT")
    return region, text, strictness


def validate_one(router: MarketRouter, body: dict) -> dict:
    region, text, strictness = request_text(body)
    threshold = request_threshold(body)
    router.engine(region)  # 第一次请求某个市场时加载参考数据，不计入耗时
    t = time.perf_counter()
    out = router.validate(region, text, strictness, threshold, body.get("geoResult"))
    out["serverTimeMs"] = round((time.perf_counter() - t) * 1000, 2)
    return out


def sg_factory(args) -> Callable[[], object]:
    def make():
        db = ReferenceDB.load(args.reference)
        if args.attributes:
            db.load_building_attributes(args.attributes)
        validator = Validator(db)
        if args.confidence_model and Path(args.confidence_model).exists():
            from .bayes import ConfidenceModel, ConfidenceValidator
            validator = ConfidenceValidator(validator, ConfidenceModel.load(args.confidence_model))
        if args.llm_endpoint:
            from .llm_fallback import LLMAssistedValidator, LocalLLM
            validator = LLMAssistedValidator(
                validator, LocalLLM(endpoint=args.llm_endpoint, model=args.llm_model, api=args.llm_api))
        return validator
    return make


def main() -> None:
    default_ref = ROOT / "data" / "reference_sg_2026.csv.gz"
    if not default_ref.exists():
        default_ref = ROOT / "data" / "reference_sg.csv.gz"
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--markets", default="SG," + ",".join(MARKETS),
                    help="开放的市场（逗号分隔）；SG 用新加坡专用引擎，其余用多市场引擎")
    ap.add_argument("--parser", default="hybrid", choices=["rules", "crf", "hybrid"],
                    help="多市场引擎的解析方式：规则 / 机器学习（CRF）/ 两者都出候选、参考数据裁决")
    ap.add_argument("--preload", action="store_true", help="启动时加载全部市场（默认第一次请求时加载）")
    ap.add_argument("--reference", default=str(default_ref), help="新加坡参考库")
    ap.add_argument("--attributes", help="可选：新加坡楼栋属性 CSV（postal,max_floor）")
    ap.add_argument("--confidence-model", default=str(ROOT / "models" / "confidence_sg.json"),
                    help="新加坡贝叶斯置信度模型（scripts/evaluate_bayes.py 生成）；传空字符串则不输出置信度")
    ap.add_argument("--llm-endpoint", help="可选：本地模型服务地址（如 http://127.0.0.1:11434），开启新加坡小模型兜底")
    ap.add_argument("--llm-model", default="qwen2.5:1.5b", help="新加坡兜底 / --intl-llm 为接口地址时的模型名")
    ap.add_argument("--intl-llm", help="可选：多市场引擎的本地小模型兜底。GGUF 文件路径（进程内 llama.cpp），"
                                       "或 OpenAI 兼容接口地址（如 http://127.0.0.1:8081）。见 docs/13 第 6 节")
    ap.add_argument("--intl-llm-markets", default="PH,AE,SA",
                    help="开启小模型兜底的市场（开发集上有提升的：菲律宾、阿联酋、沙特；泰国反而下降）；ALL = 全部")
    ap.add_argument("--llm-api", default="ollama", choices=["ollama", "openai"])
    args = ap.parse_args()
    codes = [c.strip().upper() for c in args.markets.split(",") if c.strip()]
    sg = sg_factory(args) if "SG" in codes and Path(args.reference).exists() else None
    intl_llm = None
    if args.intl_llm:
        from .intl.llm import HTTPLLM, LlamaCppLLM
        intl_llm = HTTPLLM(args.intl_llm, args.llm_model) if args.intl_llm.startswith("http") \
            else LlamaCppLLM(args.intl_llm)
        print(f"多市场引擎已开启本地小模型兜底：{intl_llm.name}")
    llm_markets = None if args.intl_llm_markets.upper() == "ALL" else \
        {c.strip().upper() for c in args.intl_llm_markets.split(",") if c.strip()}
    router = MarketRouter(sg, codes, args.parser, llm=intl_llm, llm_markets=llm_markets)
    for m in router.describe():
        print(f"  {m['code']} {m['name']}（{m['cls']} 类）{'' if m['available'] else '：参考数据未构建，暂不可用'}")
    if args.preload:
        router.preload()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(router))
    print(f"演示页面：http://{args.host}:{args.port}/    接口：POST /v1/address:validate    市场列表：GET /v1/markets")
    server.serve_forever()


if __name__ == "__main__":
    main()
