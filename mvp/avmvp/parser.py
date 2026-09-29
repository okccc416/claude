"""新加坡地址解析（规则版）：抽取邮编、单元号、楼栋号候选，其余交给召回阶段对照参考库裁决。

设计取舍：解析阶段只做"确定性高"的抽取（邮编 6 位、#楼层-单元），
楼栋号与道路名的切分存在歧义（"ANG MO KIO AVE 3 BLK 123" 里 3 和 123 都像门牌），
因此输出多个楼栋号候选，由下游用参考库验证哪种切分成立（N-best，而不是一锤定音）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .normalize import BLOCK_MARKERS, COUNTRY_TOKENS, canon_tokens, clean_text, strip_punct

_UNIT_PATTERNS = [
    # Level 5 Unit 12 / Lvl 14 #300 / Floor 3, #05
    re.compile(r"\b(?:LEVEL|LVL|LV|FLOOR|FLR)\s*(B?\d{1,2})\s*,?\s*(?:UNIT\s*#?|#)\s*(\d{1,5}[A-Z]?)\b"),
    re.compile(r"\bUNIT\s*#?\s*(B?\d{1,3})\s*[-–]\s*(\d{1,5}[A-Z]?)\b"),
    re.compile(r"#\s*(B?\d{1,3})\s*[-–]\s*(\d{1,5}[A-Z]?)\b"),
    re.compile(r"(?<![\w#-])(\d{2})\s*-\s*(\d{2,5}[A-Z]?)(?![\w-])"),
]
_LEVEL_ONLY = re.compile(r"\b(?:LEVEL|LVL|FLOOR|FLR)\s*(B?\d{1,2})\b")
_BAD_UNIT = re.compile(r"#\s*[\w-]*")
_POSTAL6 = re.compile(r"(?:\b(?:SINGAPORE|SPORE|SG|S)\s*\(?\s*)?(?<!\d)(\d{6})(?!\d)\s*\)?")
_POSTAL5 = re.compile(r"(?:\b(?:SINGAPORE|SPORE|SG|S)\s*\(?\s*)?(?<![\d#-])(\d{5})(?![\d-])\s*\)?")
BLOCK_RE = re.compile(r"^\d{1,4}[A-Z]?(?:-\d{1,3}[A-Z]?)?$")
_GLUED = re.compile(r"^(\d{1,4})([A-Z]{2,})$")


@dataclass
class ParsedAddress:
    raw: str
    postal: str | None = None
    postal_leading_zero_restored: bool = False
    unit_floor: str | None = None
    unit_no: str | None = None
    unit_raw: str | None = None  # 出现了 # 但格式不合法
    block_marked: str | None = None  # 紧跟 BLK/BLOCK 标记的楼栋号
    tokens: list[str] = field(default_factory=list)  # 规范化后的剩余 token（不含邮编、单元、标记）
    orig_tokens: list[str] = field(default_factory=list)  # 与 tokens 一一对应的用户原始写法（纠错前）
    country_suffix: list[str] = field(default_factory=list)  # 被剔除的结尾国家名（楼宇名可能以此结尾）
    country_prefix: list[str] = field(default_factory=list)  # 被剔除的开头国家名（楼宇名可能以此开头）
    all_tokens: list[str] = field(default_factory=list)  # 未拆出 BLK 标记前的 token（楼宇名里可能带 "BLK 652"）
    block_candidates: list[int] = field(default_factory=list)  # tokens 中可能是楼栋号的下标
    # 粘连写法的另一种切分："111CAMOY" 默认切成 111 CAMOY，另备一份 111C AMOY，交给参考库裁决
    alt_tokens: list[str] | None = None

    @property
    def unit(self) -> str | None:
        if self.unit_floor and self.unit_no:
            return f"#{self.unit_floor}-{self.unit_no}"
        if self.unit_floor:
            return f"Level {self.unit_floor.lstrip('0') or '0'}"
        return None


def parse(raw: str) -> ParsedAddress:
    p = ParsedAddress(raw=raw)
    text = clean_text(raw)

    for pat in _UNIT_PATTERNS:
        m = pat.search(text)
        if m:
            floor = m.group(1)
            p.unit_floor = floor if floor.startswith("B") else floor.zfill(2)
            p.unit_no = m.group(2)
            text = text[: m.start()] + " " + text[m.end():]
            break
    if p.unit_floor is None:
        m = _LEVEL_ONLY.search(text)
        if m:
            p.unit_floor = m.group(1) if m.group(1).startswith("B") else m.group(1).zfill(2)
            text = text[: m.start()] + " " + text[m.end():]
    if p.unit_floor is None:
        m = _BAD_UNIT.search(text)
        if m and m.group(0).strip("# "):
            p.unit_raw = m.group(0).strip()
            text = text[: m.start()] + " " + text[m.end():]

    matches = list(_POSTAL6.finditer(text))
    if matches:
        m = matches[-1]
        p.postal = m.group(1)
        text = text[: m.start()] + " " + text[m.end():]
    else:
        # Excel 等工具常把 018956 存成 18956：5 位数字且无 6 位邮编时，补回前导 0
        matches = list(_POSTAL5.finditer(text))
        if matches:
            m = matches[-1]
            p.postal = "0" + m.group(1)
            p.postal_leading_zero_restored = True
            text = text[: m.start()] + " " + text[m.end():]

    raw_tokens = strip_punct(text).split()
    alt = []
    for i, t in enumerate(raw_tokens):  # 10BAYFRONT -> 10 BAYFRONT（另备 10B AYFRONT）
        m = _GLUED.match(t)
        if m:
            raw_tokens[i] = f"{m.group(1)} {m.group(2)}"
            alt.append((i, f"{m.group(1)}{m.group(2)[0]} {m.group(2)[1:]}"))
    alt_raw = None
    if alt:
        alt_raw = list(raw_tokens)
        for i, v in alt:
            alt_raw[i] = v
        alt_raw = " ".join(alt_raw).split()
    raw_tokens = " ".join(raw_tokens).split()
    tokens = canon_tokens(raw_tokens)
    tokens = [t for t in tokens if t != "SPORE"]
    while tokens and tokens[-1] in COUNTRY_TOKENS:
        p.country_suffix.insert(0, tokens.pop())
    while tokens and tokens[0] in COUNTRY_TOKENS:
        p.country_prefix.append(tokens.pop(0))
    if tokens[:2] == ["REPUBLIC", "OF"]:
        tokens = tokens[2:]

    p.all_tokens = list(tokens)
    out: list[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in BLOCK_MARKERS and i + 1 < len(tokens) and BLOCK_RE.match(tokens[i + 1]):
            if p.block_marked is None:
                p.block_marked = tokens[i + 1]
            i += 2
            continue
        out.append(t)
        i += 1
    p.tokens = out
    p.orig_tokens = list(out)
    if p.block_marked is None:
        p.block_candidates = [i for i, t in enumerate(out) if BLOCK_RE.match(t)]
    if alt_raw:
        q = parse_tokens_only(alt_raw)
        if q != out:
            p.alt_tokens = q
    return p


def parse_tokens_only(raw_tokens: list[str]) -> list[str]:
    """对另一种切分做同样的规范化与标记剥离（用于粘连写法的备选切分）。"""
    tokens = [t for t in canon_tokens(raw_tokens) if t != "SPORE"]
    while tokens and tokens[-1] in COUNTRY_TOKENS:
        tokens.pop()
    while tokens and tokens[0] in COUNTRY_TOKENS:
        tokens.pop(0)
    return [t for i, t in enumerate(tokens)
            if not (t in BLOCK_MARKERS and i + 1 < len(tokens) and BLOCK_RE.match(tokens[i + 1]))]
