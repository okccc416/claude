"""多市场输入的噪声剥离：把不是地址的内容从输入里分出来，单独返回（nonAddressInfo），不丢弃。

处理顺序（确定性高的先剥，它们还会干扰门牌 / 邮编识别）：
  1. 格式残留：HTML 标签和实体（<br>、&amp;）、字面的 \\n、零宽字符
  2. 有固定格式的：网址、邮箱、坐标（十进制 / 度分秒）、Plus Code、Makani、邮政信箱、电话（含"Tel: / HP: / هاتف"
     这类标签后面的号码、巴西 (11) 98765-4321）、订单号（Order # / Bestellnr. / Pedido / Pesanan …）、
     营业时间（Mo-Fr 9-18 Uhr、Seg a Sex 8h às 18h；营业时间里的 9:00 不能当门牌）
  3. "Address: / Dirección: / Endereço: / العنوان:"这类标签
  4. 按逗号分段逐段判断（判断前先问参考库：这段完整对上道路 / 片区 / 楼名就保留）：
     - 收件人：段首是 Attn / z. Hd. / A/C / Atención / Alla c.a. / Penerima / المستلم … 的段
     - 公司名：以 GmbH / S.A. de C.V. / Ltda. / Sp. z o.o. / Sdn Bhd / LLC … 结尾、没有数字的段（印尼 PT / CV 开头）
     - 配送备注：没有数字、含 bitte / favor / dejar / titip / الرجاء … 这类配送用语的段
     - 方位描述：第几栋 / 第几间（third house、segunda casa、rumah ketiga）的段整段剥出；
       "在某物后面 / 对面 / 旁边"的段：参照物名称单独记下，只拿去找楼宇 / 商户，不拿去匹配道路
"""

from __future__ import annotations

import html
import re
import unicodedata

PHONE = re.compile(r"(?:\+|00)\d{1,3}[\s\-]?\(?\d{1,4}\)?(?:[\s\-]?\d{2,4}){2,4}|(?<![\d/])0\d{8,10}(?![\d/])|"
                   r"(?<![\d/])[89]\d{3}\s?\d{4}(?![\d/])")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
URL = re.compile(r"https?://\S+|www\.\S+")
PLUS_CODE = re.compile(r"\b[23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3}\b", re.I)
MAKANI = re.compile(r"(?<!\d)\d{5}\s\d{5}(?!\d)")
LATLNG = re.compile(r"(?<![\d.])(-?\d{1,2}\.\d{4,})\s*,\s*(-?\d{1,3}\.\d{4,})(?![\d.])")  # 直接贴的坐标
DMS = re.compile(r"(\d{1,2})°\s*(\d{1,2})['′]\s*(\d{1,2}(?:[.,]\d+)?)?[\"″]?\s*([NS])[,\s]+"
                 r"(\d{1,3})°\s*(\d{1,2})['′]\s*(\d{1,2}(?:[.,]\d+)?)?[\"″]?\s*([EW])", re.I)  # 56°57'10.9"N 24°05'11.3"E
PO_BOX = re.compile(r"(?:\bP\.?\s?O\.?\s?BOX|\bPOB|\bPOSTBUS|\bPOSTFACH|\bBOITE POSTALE|ص\.?\s?ب)\s*[.:#]?\s*(\d{2,7})\b", re.I)

_PHONE_LABEL = re.compile(
    r"(?:\b(?:tel(?:e?fone?|[eé]fono|efon|p)?|t[eé]l(?:[eé]phone)?|phone|ph|hp|h/p|mobile?|mob|cell(?:ular)?|cel|fone|"
    r"whats\s?app|wa|handphone|fax|kontakt|contact[oe]?)\b\.?|هاتف|جوال|موبايل|تلفون)"
    r"\s*(?:no\.?|nr\.?|n[°º]\.?)?\s*[:：.]?\s*(\+?\(?\d[\d\s\-().]{5,18}\d)", re.I)
_PHONE_BR = re.compile(r"\(\d{2}\)\s?9?\d{4}-?\d{4}")
_ORDER = re.compile(
    r"\b(?:no\.?\s*)?(?:order|bestell(?:ung|nr|nummer)?|auftrag(?:snr)?|commande|pedido|ordine|zam[oó]wienie|pesanan|"
    r"invoice|rechnung|factura|fatura|facture|tracking|awb)\b\.?\s*(?:no\.?|nr\.?|n[°º.]?|#|id|number|n[uú]mero|num\.?)?"
    r"\s*[:#.]?\s*(?=[A-Za-z0-9\-]*\d)[A-Za-z0-9][A-Za-z0-9\-]{3,}", re.I)
_DAY = (r"(?:mon(?:day)?|tue(?:s(?:day)?)?|wed(?:nesday)?|thu(?:r(?:s(?:day)?)?)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?|"
        r"mo|di|mi|do|fr|sa|so|montag|freitag|samstag|sonntag|lun(?:di|es)?|mar(?:di|tes)?|mer(?:credi)?|"
        r"mi[eé](?:rcoles)?|jeu(?:di)?|jue(?:ves)?|ven(?:dredi|erd[iì])?|vie(?:rnes)?|sam(?:edi)?|s[aá]b(?:ado)?|"
        r"dim(?:anche)?|dom(?:ingo|enica)?|seg(?:unda)?|ter(?:[cç]a)?|qua(?:rta)?|qui(?:nta)?|sex(?:ta)?|"
        r"pon(?:iedzia[lł]ek)?|wt|[sś]r|czw|pt|pi[aą]tek|sob(?:ota)?|niedz(?:iela)?|nd|"
        r"senin|selasa|rabu|kamis|jumat|sabtu|minggu)")
_DAY_AR = r"(?:السبت|الأحد|الاثنين|الثلاثاء|الأربعاء|الخميس|الجمعة)"
_TO = r"(?:-|–|—|a|à|às|al|au|bis|to|till|until|do|s/d|sampai|hingga|ao)"
_TIME = r"\d{1,2}(?:[:.h]\d{2})?\s*(?:h|uhr|hrs?|am|pm)?"
_HOURS = re.compile(
    rf"(?:\b{_DAY}\.?(?:-feira)?\s*{_TO}\s*{_DAY}\b\.?(?:-feira)?|{_DAY_AR}\s*{_TO}?\s*{_DAY_AR})"
    rf"(?:\s*[:,]?\s*{_TIME}\s*{_TO}\s*{_TIME})?"
    r"|\b\d{1,2}(?::\d{2}|h\d{0,2}|\s*(?:uhr|am|pm))\s*(?:-|–|a|à|às|bis|to)\s*\d{1,2}(?::\d{2}|h\d{0,2}|\s*(?:uhr|am|pm))"
    r"|\b\d{1,2}\s*-\s*\d{1,2}\s*uhr\b", re.I)
_LABEL = re.compile(
    r"(?:^|(?<=[,;\n|]))\s*(?:(?:shipping|delivery|billing|mailing|postal|street|home|work|business)\s+)?"
    r"(?:address|addr|adresse|anschrift|lieferadresse|rechnungsadresse|direcci[oó]n|domicilio|endere[cç]o|indirizzo|"
    r"adres|alamat|地址|住所|العنوان)\s*[:：]", re.I)
_RECIPIENT = re.compile(
    r"^\s*(?:(?:attn|attention|c/o|recipient|receiver|consignee|ship\s+to|deliver\s+to|z\.\s?hd\.?|zu\s+h[äa]nden(?:\s+von)?|"
    r"empf[äa]nger|[àa]\s+l'attention\s+de|attention\s+de|destinataire|atenci[oó]n(?:\s+a)?|a/c|aos\s+cuidados\s+de|"
    r"destinat[aá]rio|alla\s+c\.\s?a\.?|all'attenzione\s+di|destinatario|do\s+r[ąa]k(?:\s+w[łl]asnych)?|odbiorca|"
    r"penerima|kepada|u\.p\.|yth\.?)(?=[\s:：.])|المستلم|إلى|to(?=\s*[:：]))\s*[:：.]?\s*", re.I)
_LEGAL = re.compile(
    r"(?:\b(?:gmbh(?:\s*&\s*co\.?\s*kg)?|ag|kg|ohg|ug|sarl|s\.a\.r\.l\.|sas|eurl|s\.\s?a\.(?:\s*de\s*c\.\s?v\.)?|"
    r"s\.\s?l\.|s\.r\.l\.|srl|s\.p\.a\.|spa|ltda|ltd|limited|llc|l\.l\.c\.|inc|corp|pty\.?\s*ltd|pte\.?\s*ltd|"
    r"sdn\.?\s*bhd|bhd|tbk|sp\.\s?z\s?o\.\s?o|sp\.\s?j|b\.v|bv|n\.v|nv|ab|a/s|as|oy|oyj|plc|kft|zrt|s\.r\.o|d\.o\.o|"
    r"oü|sia|uab)\.?|ооо|ООО)\s*$", re.I)
_LEGAL_PREFIX = re.compile(r"^\s*(?:PT|CV)\.?\s+\S+\s+\S+", re.I)  # 印尼 / 马来西亚：PT Maju Jaya
_ARTICLES = r"(?:THE|DER|DIE|DAS|DEM|DEN|DES|LE|LA|LES|L|EL|LOS|LAS|IL|LO|O|A|OS|AS|DO|DA|DOS|DAS|DU|AL)"
# 配送用语（大写、去重音后比较）；不收 RING / TOR 这类会出现在路名里的词
NOTE_WORDS = {
    "PLEASE", "PLS", "PLZ", "KINDLY", "LEAVE", "CALL", "DELIVER", "DELIVERY", "RECEPTION", "DOORBELL", "KNOCK", "FRAGILE",
    "URGENT", "ASAP", "COD", "NEIGHBOUR", "NEIGHBOR", "BITTE", "ABGEBEN", "KLINGELN", "NACHBARN", "NACHBAR", "ZUSTELLEN",
    "LIEFERUNG", "BRIEFKASTEN", "MERCI", "LAISSER", "SONNER", "GARDIEN", "LIVRAISON", "APPELER", "LIVRER", "FAVOR",
    "DEJAR", "LLAMAR", "PORTERO", "ENTREGAR", "TIMBRE", "LASCIARE", "PORTIERE", "CITOFONARE", "CONSEGNA", "CHIAMARE",
    "DEIXAR", "PORTARIA", "LIGAR", "CAMPAINHA", "PROSZE", "ZOSTAWIC", "SASIADA", "DZWONIC", "DOSTAWA", "TITIP", "SATPAM",
    "TELEPON", "TOLONG", "HUBUNGI", "الرجاء", "الاتصال", "التوصيل"}
# 方位描述：序数 + 房屋 / 门（第三栋、segunda casa、rumah ketiga）
_ORD = (r"(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|LAST|\d(?:ST|ND|RD|TH)|ERSTE[NSRM]?|ZWEITE[NSRM]?|DRITTE[NSRM]?|VIERTE[NSRM]?|"
        r"LETZTE[NSRM]?|PREMIERE|DEUXIEME|TROISIEME|DERNIERE|PRIMER[AO]?|SEGUND[AO]|TERCER[AO]?|CUART[AO]|ULTIM[AO]|"
        r"SECONDA|TERZA|PRIMEIR[AO]|TERCEIR[AO]|PIERWSZY|DRUGI|TRZECI|OSTATNI)")
_HOUSE = (r"(?:HOUSE|BUILDING|DOOR|GATE|SHOP|HAUS|GEBAUDE|TUR|MAISON|PORTE|BATIMENT|IMMEUBLE|CASA|PUERTA|EDIFICIO|PORTON|"
          r"PORTA|PALAZZO|PREDIO|PORTAO|DOM|BUDYNEK|BRAMA|RUMAH|GEDUNG|PINTU|TOKO)")
_DESCRIBE = re.compile(rf"\b{_ORD}\s+(?:\w+\s+)?{_HOUSE}\b|\b(?:RUMAH|GEDUNG|PINTU|TOKO)\s+(?:KE\s*)?"
                       rf"(?:PERTAMA|KEDUA|KETIGA|KEEMPAT|TERAKHIR|\d)\b|(?:البيت|المنزل|الباب)\s+(?:الأول|الثاني|الثالث|الرابع|الأخير)")
# 相对方位词：参照物描述（在某物后面 / 对面 / 旁边 / 附近）。STRONG 单独成段也认；WEAK（之后 / 过了）只在"第几栋"描述里认
_STRONG = (r"(?:BEHIND|OPPOSITE|OPP|NEAR|NEXT\s+TO|BESIDE|ACROSS(?:\s+FROM)?|IN\s+FRONT\s+OF|ADJACENT\s+TO|"
           r"HINTER|NEBEN|GEGENUBER(?:\s+VO[MN])?|DERRIERE|A\s+COTE\s+D[EU]S?|EN\s+FACE\s+D[EU]S?|PRES\s+D[EU]S?|"
           r"DETRAS\s+DEL?|AL\s+LADO\s+DEL?|FRENTE\s+AL?|ENFRENTE\s+DEL?|CERCA\s+DEL?|JUNTO\s+AL?|DIETRO|"
           r"ACCANTO\s+AL?|DI\s+FRONTE\s+AL?|VICINO\s+AL?|ATRAS\s+D[OAE]S?|AO\s+LADO\s+D[OAE]S?|EM\s+FRENTE\s+A[OS]?|"
           r"PERTO\s+D[OAE]S?|PROXIMO\s+A[OS]?|NAPRZECIWKO|OBOK|DI\s+BELAKANG|BELAKANG|DI\s+DEPAN|DEPAN|SEBELAH|DEKAT|"
           r"BERHADAPAN|TRUOC|SAU|GAN|KE\s+BEN)")
_WEAK = (r"(?:AFTER|PAST|NACH\s+DE[MRN]|APRES|DESPUES\s+DEL?|DOPO|DEPOIS\s+D[OAE]S?|ZA|KOLO|SETELAH|SESUDAH)")
_AR_REL = r"(?:خلف|مقابل|بجانب|قرب|امام|أمام)"
LANDMARK = re.compile(rf"\b{_STRONG}\b|{_AR_REL}")  # 引擎用来标 LANDMARK_RELATIVE（输入先 fold 成大写、去重音）
_REL_ANY = re.compile(rf"\b(?:{_STRONG}|{_WEAK})\s+|(?:{_AR_REL}|بعد)\s+")
_REL_STRONG = re.compile(rf"\b{_STRONG}\s+|{_AR_REL}\s+")
LEADING_ARTICLE = re.compile(rf"^{_ARTICLES}\s+")  # 参照物前的冠词：hinter der Post / behind the station


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).upper().replace("Ł", "L")


def known_segment(ref, seg: str) -> bool:
    """这一段完整对上参考库里的道路 / 片区 / 楼名（或去掉类型词后的道路核心名）：是地址的一部分，不当噪声。"""
    if ref is None:
        return False
    from .text import core_key, key
    k = " ".join(key(seg, ref.market).split())
    if not k:
        return False
    if k in ref.street_keys or k in ref.area_keys:
        return True
    ck = core_key(seg, ref.market)
    if len(ck) >= 5 and ck in ref.street_core:
        return True
    pf = getattr(ref, "poi_fuzzy", None)
    return bool(pf is not None and hasattr(pf, "get") and len(k) >= 6 and pf.get(k))


def strip_noise(raw: str, ref=None) -> tuple[str, dict[str, list[str]], dict[str, str]]:
    noise: dict[str, list[str]] = {}
    codes: dict[str, str] = {}

    def add(name: str, value: str) -> None:
        value = value.strip(" ,;:-")
        if value:
            noise.setdefault(name, []).append(value)

    text = raw or ""
    if "<" in text or "&" in text:
        text = re.sub(r"<\s*(?:br|/p|/div|/li|/tr|p|div|li)\b[^>]{0,40}>", ", ", text, flags=re.I)
        text = re.sub(r"<[^<>]{1,60}>", " ", text)
        text = html.unescape(text)
    text = re.sub(r"\\[nrt]|[\r\n\t]+", ", ", text)
    text = re.sub(r"[\u200b-\u200d\u2060\ufeff]", "", text)
    for name, rx in (("urls", URL), ("emails", EMAIL)):
        found = rx.findall(text)
        if found:
            noise[name] = found
            text = rx.sub(" ", text)
    m = DMS.search(text)
    if m:
        def deg(d, mi, s):
            return float(d) + float(mi) / 60 + float((s or "0").replace(",", ".")) / 3600
        lat = deg(*m.group(1, 2, 3)) * (-1 if m.group(4).upper() == "S" else 1)
        lng = deg(*m.group(5, 6, 7)) * (-1 if m.group(8).upper() == "W" else 1)
        codes["latlng"] = f"{lat:.6f},{lng:.6f}"
        text = text[:m.start()] + " " + text[m.end():]
    m = LATLNG.search(text)
    if m:
        codes["latlng"] = f"{m.group(1)},{m.group(2)}"
        text = text[:m.start()] + " " + text[m.end():]
    for name, rx in (("plus_code", PLUS_CODE), ("makani", MAKANI)):
        m = rx.search(text)
        if m:
            codes[name] = m.group(0).upper()
            text = text[:m.start()] + " " + text[m.end():]
    boxes = PO_BOX.findall(text)
    if boxes:  # 中东常把邮政信箱号填在邮编栏
        noise["poBoxes"] = boxes
        text = PO_BOX.sub(" ", text)
    for rx, name in ((_PHONE_LABEL, "phones"), (_PHONE_BR, "phones"), (_ORDER, "orderRefs"), (_HOURS, "openingHours")):
        def repl(m, name=name):
            add(name, m.group(1) if name == "phones" and m.re is _PHONE_LABEL else m.group(0))
            return " , "
        text = rx.sub(repl, text)
    phones = PHONE.findall(text)
    if phones:
        noise.setdefault("phones", []).extend(p.strip() for p in phones)
        text = PHONE.sub(" ", text)
    text = _LABEL.sub(" ", text)

    kept: list[str] = []
    for seg in re.split(r"[,;|،]+", text):
        seg = seg.strip()
        if not seg.strip(" .-"):
            continue
        has_digit = bool(re.search(r"\d", seg))
        up = _fold(seg)
        words = re.findall(r"[^\W\d_]+", up)
        m = _RECIPIENT.match(seg)
        if m:
            body = seg[m.end():].strip()
            if not has_digit:
                add("recipients", body)
                continue
            toks = list(re.finditer(r"\S+", body))  # 同一段里人名后面直接跟着地址：最多切掉 4 个词的人名
            n = 0
            while n < len(toks) and n < 4 and toks[n].group(0).replace(".", "").isalpha():
                n += 1
            if 0 < n < len(toks):
                add("recipients", body[:toks[n - 1].end()])
                seg, up = body[toks[n].start():].strip(), _fold(body[toks[n].start():])
                has_digit = bool(re.search(r"\d", seg))
        if _DESCRIBE.search(up) or _DESCRIBE.search(seg):
            add("descriptions", seg)
            m = _REL_ANY.search(up) or _REL_ANY.search(seg)
            target = (up if m.string is up else seg)[m.end():].strip() if m else ""
            if has_digit:  # "third house behind Horstweg 53C"：参照物本身是个地址，照常解析，但结论最多 CONFIRM
                kept.append(target or seg)
                add("relativeTo", target or seg)
            elif target:
                add("landmarks", target)
            continue
        if known_segment(ref, seg):
            kept.append(seg)
            continue
        legal = _LEGAL.search(seg) if not has_digit and len(words) >= 2 else None
        if legal and known_segment(ref, seg[:legal.start()]):
            legal = None  # Baden AG：前面是地名，AG 是州名缩写，不是公司
        if legal or (not has_digit and len(words) >= 3 and ref is not None and ref.market in ("ID", "MY")
                     and _LEGAL_PREFIX.match(seg)):
            add("organizations", seg)
            continue
        if not has_digit and (set(words) & NOTE_WORDS or any(w in seg for w in ("الرجاء", "الاتصال", "التوصيل"))):
            add("notes", seg)
            continue
        m = _REL_STRONG.search(up) if not has_digit else None
        if m is None and not has_digit:
            m = _REL_STRONG.search(seg)
        if m:
            # "frente al parque" / "Avenida Paulista, perto do metrô"：方位词后面是参照物，只拿去找楼宇 / 商户，不拿去匹配道路
            src = up if m.string is up else seg
            add("landmarks", src[m.end():])
            if src[:m.start()].strip(" .-"):
                kept.append(src[:m.start()].strip(" .-"))
            continue
        kept.append(seg)
    return ", ".join(kept), noise, codes
