"""业务噪声剥离：把电话、邮箱、订单号、收件人、公司名、配送备注等非地址信息从输入里分离出来。

原则：
- 确定性高的先剥（邮箱、电话、订单号、中文备注），它们还会干扰邮编识别（订单号里常有 6 位数字）
- 按分隔符切段后逐段判断；判断"是不是噪声"之前，先问参考库"这段像不像地址"（道路 / 楼宇名命中就保留），
  避免把 "Brilliant Student Care" 这类真实楼宇名当成备注删掉
- 剥离出来的内容不丢弃，作为 nonAddressInfo 返回，物流客户正好需要把电话和备注拆成独立字段
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.I)
_PHONE_LABEL = r"(?:TEL(?:EPHONE)?|PHONE|PH|HP|H/P|MOBILE|MOB|CONTACT(?:\s*NO)?|WHATSAPP|WA)\.?\s*[:：]?\s*"
_PHONE = re.compile(
    r"(?:\b" + _PHONE_LABEL + r")?(?<![\d#-])(?:\(?\+?65\)?[\s-]?)?[3689]\d{3}[\s-]?\d{4}(?![\d-])", re.I)
_ORDER = re.compile(
    r"\b(?:ORDER(?:\s*ID)?|ORD|PO|SO|INV(?:OICE)?|REF|TRACKING|TRK|AWB)\s*(?:NO\.?|NUMBER|ID)?\s*[#:：.]?\s*"
    r"(?=[A-Z0-9-]*\d)[A-Z0-9][A-Z0-9-]{3,}", re.I)
_CJK = re.compile(r"[\u3000-\u303f\u3400-\u9fff\uf900-\ufaff]+")
_SPLIT = re.compile(r"[,;|\n()（）\[\]]+|\s+-\s+|\s+/\s+")
_ORG = re.compile(r"\b(?:PTE\.?\s*LTD\.?|PTE\.?|LTD\.?|LLP|LIMITED|INC\.?|CORP(?:ORATION)?\.?|COMPANY|CO\.)(?=\s|$)")
_RECIPIENT_PREFIX = re.compile(
    r"^(?:ATTN|ATTENTION|TO|RECIPIENT|RECEIVER|NAME|CONSIGNEE)\s*[:：.]?\s+", re.I)
_HONORIFIC = re.compile(r"^(?:MR|MRS|MS|MDM|MISS|DR|MADAM)\.?\s+[A-Z]", re.I)
# 明确的配送指令词；刻意不收 CARE / HANDLE / INSIDE 等可能出现在楼宇名里的词
_NOTE_WORDS = {
    "PLS", "PLEASE", "PLZ", "KINDLY", "CALL", "LEAVE", "DOOR", "DOORSTEP", "GUARD", "GUARDHOUSE", "SECURITY",
    "RECEPTION", "CONCIERGE", "ARRIVAL", "DELIVER", "DELIVERY", "DELIVERED", "WEEKDAYS", "WEEKENDS", "WEEKDAY",
    "WEEKEND", "THANKS", "THANK", "THX", "TQ", "RING", "DOORBELL", "BELL", "KNOCK", "DONT", "DON'T", "FRAGILE", "URGENT",
    "ASAP", "COD", "NEIGHBOUR", "NEIGHBOR", "LETTERBOX", "MAILBOX", "SMS", "WHATSAPP", "PASSCODE", "B4", "REACH",
}
# 段内尾部备注的起始词；不收 RING（Woodlands Ring Road）等可能是路名一部分的词
_NOTE_START = {"PLS", "PLEASE", "PLZ", "KINDLY", "CALL", "LEAVE", "DELIVER", "THANKS", "THX", "TQ",
               "KNOCK", "DONT", "DON'T", "FRAGILE", "URGENT", "ASAP", "COD", "SMS", "NO"}
_NAME_STOP = {"BLK", "BLOCK", "NO", "UNIT", "LEVEL", "LVL"}


@dataclass
class NoiseResult:
    text: str  # 剥离后的地址文本
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    order_refs: list[str] = field(default_factory=list)
    recipients: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def removed_any(self) -> bool:
        return any((self.phones, self.emails, self.order_refs, self.recipients, self.organizations, self.notes))

    def as_dict(self) -> dict:
        d = {"phones": self.phones, "emails": self.emails, "orderRefs": self.order_refs,
             "recipients": self.recipients, "organizations": self.organizations, "notes": self.notes}
        return {k: v for k, v in d.items() if v}


def _words(seg: str) -> list[str]:
    return re.findall(r"[A-Z0-9']+", seg.upper())


def strip_noise(raw: str, looks_like_address: Callable[[str], bool]) -> NoiseResult:
    """looks_like_address(段落文本) 由调用方提供：该段能在参考库里命中道路或楼宇名时返回 True。"""
    text = unicodedata.normalize("NFKC", raw or "")  # 全角数字 / 字母转半角
    res = NoiseResult(text="")

    def take(pattern, bucket, s):
        def repl(m):
            bucket.append(m.group(0).strip(" ,;"))
            return " , "
        return pattern.sub(repl, s)

    text = take(_EMAIL, res.emails, text)
    text = take(_ORDER, res.order_refs, text)
    text = take(_PHONE, res.phones, text)
    text = take(_CJK, res.notes, text)
    text = re.sub(r"\bC/O\b", "ATTN", text, flags=re.I)
    # "# 03 - 160" 里的 " - " 不是分段符
    text = re.sub(r"#\s*(B?\d{1,3})\s*[-–]\s*(\d{1,5}[A-Z]?)", r"#\1-\2", text)
    # S(018956) / Singapore (018956) 这类邮编写法里的括号不是分段符
    text = re.sub(r"\b(S|SG|SINGAPORE)\s*[(（]\s*(\d{6})\s*[)）]", r"\1 \2", text, flags=re.I)

    segments = [s.strip() for s in _SPLIT.split(text) if s and s.strip(" .-")]
    kept: list[str] = []
    has_digit_elsewhere = [any(ch.isdigit() for s in segments[:i] + segments[i + 1:] for ch in s)
                           for i in range(len(segments))]
    for i, seg in enumerate(segments):
        up = seg.upper().strip(" .")
        words = _words(up)
        if not words:
            continue
        address_like = looks_like_address(up)
        if _RECIPIENT_PREFIX.match(up) and not any(ch.isdigit() for ch in up):
            res.recipients.append(_RECIPIENT_PREFIX.sub("", seg).strip())
            continue
        if _HONORIFIC.match(up) and not any(ch.isdigit() for ch in up) and not address_like:
            res.recipients.append(seg)
            continue
        if (_RECIPIENT_PREFIX.match(up) or _HONORIFIC.match(up)) and any(ch.isdigit() for ch in up):
            # 没有分隔符的 "TO: DANIEL LEE BLK26 ..."：切出前面的人名（最多 4 个词，遇到数字或楼栋标记即停）
            body = _RECIPIENT_PREFIX.sub("", seg) if _RECIPIENT_PREFIX.match(up) else seg
            toks = list(re.finditer(r"\S+", body))
            n = 0
            while (n < len(toks) and n < (5 if _HONORIFIC.match(up) else 4) and toks[n].group(0).isalpha()
                   and toks[n].group(0).upper() not in _NAME_STOP):
                n += 1
            if 0 < n < len(toks):
                res.recipients.append(body[: toks[n - 1].end()].strip())
                seg = body[toks[n].start():].strip()
                up = seg.upper()
                words = _words(up)
                address_like = looks_like_address(up)
        org = _ORG.search(up)
        if org and not address_like:
            # "ABC Pte Ltd 10 Anson Road"：公司名后面还跟着地址时，只切掉公司名部分
            head, tail = seg[: org.end()], seg[org.end():]
            res.organizations.append(head.strip())
            if tail.strip(" .,"):
                kept.append(tail.strip(" .,"))
            continue
        if not address_like and any(w in _NOTE_WORDS for w in words) and not re.search(r"\d{6}|#", up):
            res.notes.append(seg)
            continue
        # 段内尾部的配送指令："... 018956 pls leave at door"
        cut = next((k for k, w in enumerate(words) if w in _NOTE_START and k > 0
                    and any(x in _NOTE_WORDS for x in words[k:])), None)
        if cut is not None and not re.search(r"\d{6}|#", " ".join(words[cut:])):
            pos = [m.start() for m in re.finditer(r"[A-Z0-9']+", up)][cut]
            head, tail = seg[:pos].strip(), seg[pos:].strip()
            # 只有"前半段像地址、后半段不像地址"时才切，避免把路名切断
            if (looks_like_address(head.upper()) or re.search(r"\d{6}", head)) and not looks_like_address(tail.upper()):
                res.notes.append(tail)
                seg = head
        # 没有任何标记的首段人名：在最前面、全是字母、不像地址，且后面的段落里有数字
        if (i == 0 and len(segments) > 1 and not address_like and has_digit_elsewhere[i]
                and 1 <= len(words) <= 4 and all(w.isalpha() for w in words)):
            res.recipients.append(seg)
            continue
        if seg:
            kept.append(seg)
    res.text = ", ".join(kept)
    return res
