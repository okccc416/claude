"""噪声鲁棒性测试：取开发集里引擎原本定位对的真实地址，按当地语言注入各类噪声，看结论还对不对。

噪声类型（每类按市场语言给写法）：
  电话、邮箱、收件人、公司名、配送备注、营业时间、订单号、"地址："这类标签、占位值（N/A、-）、重复的城市 / 国家、
  HTML 标签和转义换行、表情符号、全角数字、参照物描述、楼层 / 单元、全小写 / 全大写、去掉逗号、乱序（城市邮编挪到最前）、
  以上多种叠加；另外单独测"只有描述、没有地址"的输入（第三棵树后面第二栋房子）。

指标：仍然定位对的比例、直接通过但错了（静默错误）的比例、变成 FIX 的比例。

  python scripts/noise_robustness.py [--markets DE,GB,...] [--n 40] [--jobs 4]
输出：reports/noise_robustness.md、reports/noise_robustness.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from avmvp.intl.engine import ACCEPT, Engine  # noqa: E402
from avmvp.intl.markets import MARKETS  # noqa: E402
from evaluate_markets import judge_real, real_cases  # noqa: E402

DEFAULT = "AU,GB,IE,DE,FR,ES,IT,PT,PL,BR,MX,CL,IN,ID,AE"
T = {  # 各语言的噪声写法；没有的语言用英文
    "phone": {"EN": "Tel: +44 20 7946 0958", "DE": "Tel. +49 30 12345678", "FR": "Tél : 01 42 68 53 00",
              "ES": "Tel: 912 345 678", "IT": "Tel. 02 1234 5678", "PT": "Tel: (11) 98765-4321",
              "PL": "tel. 22 123 45 67", "ID": "HP: 0812-3456-7890", "AR": "هاتف 050 123 4567"},
    "email": {"EN": "Email: orders@example.com"},
    "recipient": {"EN": "Attn: John Smith", "DE": "z. Hd. Herrn Thomas Müller", "FR": "À l'attention de M. Pierre Martin",
                  "ES": "Atención: Sr. Juan Pérez", "IT": "Alla c.a. Sig. Mario Rossi", "PT": "A/C Sr. João Silva",
                  "PL": "Do rąk: Jan Kowalski", "ID": "Penerima: Budi Santoso", "AR": "المستلم: محمد أحمد"},
    "company": {"EN": "Acme Trading Ltd", "DE": "Müller Logistik GmbH", "FR": "Société Dupont SARL",
                "ES": "Distribuciones García S.A. de C.V.", "IT": "Rossi Forniture S.r.l.", "PT": "Comercial Silva Ltda.",
                "PL": "Kowalski Sp. z o.o.", "ID": "PT Maju Jaya Abadi", "AR": "Al Noor Trading LLC"},
    "note": {"EN": "please leave at reception, call before delivery", "DE": "bitte beim Nachbarn abgeben",
             "FR": "merci de laisser chez le gardien", "ES": "dejar con el portero, llamar antes de entregar",
             "IT": "lasciare al portiere", "PT": "favor deixar na portaria", "PL": "proszę zostawić u sąsiada",
             "ID": "titip di pos satpam, telepon dulu", "AR": "الرجاء الاتصال قبل التوصيل"},
    "hours": {"EN": "Mon-Fri 9:00-18:00", "DE": "Mo-Fr 9-18 Uhr", "FR": "du lundi au vendredi 9h-18h",
              "ES": "Lunes a viernes 9:00 a 18:00", "IT": "Lun-Ven 9-18", "PT": "Seg a Sex 8h às 18h",
              "PL": "pon.-pt. 9-17", "ID": "Senin-Jumat 08.00-17.00", "AR": "السبت-الخميس 9-6"},
    "order": {"EN": "Order #A1234567", "DE": "Bestellnr. 4711-2024", "FR": "Commande n° 2024-55821",
              "ES": "Pedido 0098123", "IT": "Ordine n. 556677", "PT": "Pedido nº 778899", "PL": "Zamówienie nr 334455",
              "ID": "No. Pesanan 1122334455", "AR": "Order #A1234567"},
    "label": {"EN": "Address:", "DE": "Adresse:", "FR": "Adresse :", "ES": "Dirección:", "IT": "Indirizzo:",
              "PT": "Endereço:", "PL": "Adres:", "ID": "Alamat:", "AR": "العنوان:"},
    "landmark": {"EN": "near the train station", "DE": "gegenüber vom Bahnhof", "FR": "en face de la gare",
                 "ES": "frente al parque", "IT": "di fronte alla stazione", "PT": "em frente ao mercado",
                 "PL": "naprzeciwko dworca", "ID": "dekat masjid", "AR": "بجانب المسجد"},
    "floor_unit": {"EN": "2nd floor, Suite 210", "DE": "2. OG, Hinterhaus", "FR": "2e étage, porte B",
                   "ES": "Piso 3, Of. 301", "IT": "3° piano, interno 5", "PT": "3º andar, sala 301",
                   "PL": "II piętro, lok. 5", "ID": "Lantai 2, Unit 5", "AR": "الطابق 2، مكتب 5"},
    # 只有描述、没有地址：{0} 填参考库里的一个真实商户名
    "describe_poi": {"EN": "third house behind {0}", "DE": "drittes Haus hinter {0}", "FR": "troisième maison derrière {0}",
                     "ES": "tercera casa detrás de {0}", "IT": "terza casa dietro {0}", "PT": "terceira casa atrás do {0}",
                     "PL": "trzeci dom za {0}", "ID": "rumah ketiga di belakang {0}", "AR": "البيت الثالث خلف {0}"},
    "describe_only": {"EN": "second house after the big tree, blue gate", "DE": "zweites Haus nach dem großen Baum, blaues Tor",
                      "FR": "deuxième maison après le grand arbre, portail bleu",
                      "ES": "segunda casa después del árbol grande, portón azul",
                      "IT": "seconda casa dopo il grande albero, cancello blu",
                      "PT": "segunda casa depois da árvore grande, portão azul",
                      "PL": "drugi dom za dużym drzewem, niebieska brama",
                      "ID": "rumah kedua setelah pohon besar, pagar biru", "AR": "البيت الثاني بعد الشجرة الكبيرة"},
}
LANG_OF = {"PT": "PT", "BR": "PT", "ES": "ES", "MX": "ES", "CL": "ES", "AR": "ES", "CO": "ES", "PR": "ES", "DE": "DE",
           "AT": "DE", "CH": "DE", "FR": "FR", "BE": "FR", "LU": "FR", "IT": "IT", "PL": "PL", "ID": "ID", "MY": "ID",
           "AE": "AR", "SA": "AR"}
COUNTRY = {"AU": "Australia", "GB": "United Kingdom", "IE": "Ireland", "DE": "Deutschland", "FR": "France",
           "ES": "España", "IT": "Italia", "PT": "Portugal", "PL": "Polska", "BR": "Brasil", "MX": "México",
           "CL": "Chile", "IN": "India", "ID": "Indonesia", "AE": "United Arab Emirates"}
FULLWIDTH = str.maketrans("0123456789", "０１２３４５６７８９")


def t(kind: str, code: str) -> str:
    return T[kind].get(LANG_OF.get(code, "EN"), T[kind]["EN"])


def variants(code: str, text: str, rnd: random.Random) -> dict[str, str]:
    segs = [s.strip() for s in text.split(",") if s.strip()]
    tail = segs[-1] if len(segs) > 1 else ""
    city = segs[-2] if len(segs) > 2 else tail
    v = {
        "电话": f"{text}, {t('phone', code)}",
        "邮箱": f"{text} {t('email', code)}",
        "收件人": f"{t('recipient', code)}, {text}",
        "公司名": f"{t('company', code)}, {text}",
        "配送备注": f"{text}, {t('note', code)}",
        "营业时间": f"{text}, {t('hours', code)}",
        "订单号": f"{t('order', code)}, {text}",
        "标签前缀": f"{t('label', code)} {text}",
        "占位值": f"{text}, N/A, -, null",
        "重复城市 / 国家": f"{text}, {city}, {city}, {COUNTRY.get(code, '')}",
        "HTML 标签": "<p>" + text.replace(", ", "<br>") + "</p>",
        "转义换行": text.replace(", ", "\\n"),
        "表情符号": f"📍 {text} 🏠",
        "全角数字": text.translate(FULLWIDTH),
        "参照物描述": f"{text}, {t('landmark', code)}",
        "楼层 / 单元": f"{text}, {t('floor_unit', code)}",
        "全小写": text.lower(),
        "全大写": text.upper(),
        "去掉逗号": text.replace(",", ""),
        "乱序（城市邮编在前）": ", ".join(segs[-1:] + segs[:-1]) if len(segs) > 1 else text,
    }
    v["多种叠加"] = (f"{t('label', code)} {t('recipient', code)}, {t('company', code)}, {text}, "
                    f"{t('floor_unit', code)}, {t('note', code)}, {t('phone', code)}")
    return v


def run(code: str, n: int) -> dict:
    eng = Engine(code, "hybrid")
    rnd = random.Random(7)
    base = []
    for case in real_cases(code, 600, "dev"):
        r = eng.validate(case["input"])
        # 原本就定位对、而且不是只靠片区的（没有官方地址表的市场取道路 / 楼宇级）
        if judge_real(eng, r, case).startswith("正确") and r.granularity in ("PREMISE", "PREMISE_PROXIMITY", "ROUTE"):
            base.append(case)
        if len(base) >= n:
            break
    out: dict = {"n": len(base), "kinds": {}}
    for case in base:
        for kind, text in variants(code, case["input"], rnd).items():
            r = eng.validate(text)
            o = judge_real(eng, r, case)
            c = out["kinds"].setdefault(kind, Counter())
            c["n"] += 1
            c["ok"] += o.startswith("正确")
            c["silent"] += r.action == ACCEPT and not o.startswith("正确")
            c["fix"] += o.startswith("判 FIX")
            c["accept"] += r.action == ACCEPT
    # 只有描述、没有地址：不能直接通过；描述里有真实商户时应定位到商户附近并请用户确认
    pois = [row[0] for row in eng.ref.db.execute(
        "SELECT name FROM poi WHERE length(name) BETWEEN 6 AND 30 ORDER BY id LIMIT 400")][::20][:n]
    for kind, items in (("只有描述（含真实商户名）", [t("describe_poi", code).format(p) for p in pois]),
                        ("只有描述（没有任何名称）", [t("describe_only", code)] * 5)):
        c = out["kinds"].setdefault(kind, Counter())
        for text in items:
            r = eng.validate(text)
            c["n"] += 1
            c["accept"] += r.action == ACCEPT
            c["fix"] += r.action == "FIX"
            c["confirm"] += r.action not in (ACCEPT, "FIX")
            c["landmark"] += "LANDMARK_RELATIVE" in r.reasons
    out["kinds"] = {k: dict(v) for k, v in out["kinds"].items()}
    print(f"{code} done", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", default=DEFAULT)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    codes = args.markets.split(",")
    if args.jobs > 1:
        from multiprocessing import Pool
        with Pool(args.jobs) as pool:
            outs = pool.starmap(run, [(c, args.n) for c in codes])
    else:
        outs = [run(c, args.n) for c in codes]
    res = {c: o for c, o in zip(codes, outs) if o["n"]}
    (ROOT / "reports" / f"noise_robustness{args.tag}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                                                       encoding="utf-8")
    kinds = list(next(iter(res.values()))["kinds"])
    L = ["# 噪声鲁棒性（自动生成）\n",
         f"- 样本：{len(codes)} 个市场（{', '.join(codes)}）开发集里引擎原本定位对的真实地址（门牌 / 门牌附近 / 道路级），每个市场 {args.n} 条；"
         "按当地语言注入一类噪声后重新校验",
         "- 仍然对：仍然定位对的比例；静默错误：直接通过但位置错了；变成 FIX：判成请用户补充\n",
         "| 噪声类型 | 样本 | 仍然对 | 静默错误 | 变成 FIX | 最差的市场 |", "|---|---|---|---|---|---|"]
    for k in kinds:
        if k.startswith("只有描述"):
            continue
        n = sum(r["kinds"][k]["n"] for r in res.values())
        ok = sum(r["kinds"][k]["ok"] for r in res.values())
        sil = sum(r["kinds"][k]["silent"] for r in res.values())
        fix = sum(r["kinds"][k]["fix"] for r in res.values())
        worst = min(res, key=lambda c: res[c]["kinds"][k]["ok"] / max(res[c]["kinds"][k]["n"], 1))
        w = res[worst]["kinds"][k]
        L.append(f"| {k} | {n} | {ok / n:.1%} | {sil / n:.1%} | {fix / n:.1%} | {MARKETS[worst].name}（{worst}）"
                 f"{w['ok'] / w['n']:.0%} |")
    L += ["\n**只有描述、没有地址的输入**（应当：不直接通过；有真实商户名时定位到商户附近并请用户确认，没有任何名称时判 FIX）：\n",
          "| 输入 | 样本 | 直接通过 | 请用户确认 | 判 FIX | 标出\"参照物描述\" |", "|---|---|---|---|---|---|"]
    for k in kinds:
        if not k.startswith("只有描述"):
            continue
        n = sum(r["kinds"][k]["n"] for r in res.values())
        g = lambda f: sum(r["kinds"][k].get(f, 0) for r in res.values()) / n  # noqa: E731
        L.append(f"| {k} | {n} | {g('accept'):.1%} | {g('confirm'):.1%} | {g('fix'):.1%} | {g('landmark'):.1%} |")
    (ROOT / "reports" / f"noise_robustness{args.tag}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
