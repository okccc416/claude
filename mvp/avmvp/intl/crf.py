"""机器学习地址解析器：条件随机场（CRF）给每个词打标签（门牌 / 单元 / 道路 / 楼宇 / 片区 / 城市 / 邮编 / 其他）。

与 libpostal 同一路线：用参考库里的结构化地址按各国写法渲染出大量带标签样本来训练（render.py），
不需要人工标注。特征只用"词本身 + 词形 + 文字类别 + 位置 + 是否出现在道路 / 片区 / 楼宇词表里"，
不使用规则解析器的匹配结果，保证与规则方案的比较是公平的。

训练：python scripts/train_market_parsers.py；模型存为 data/markets/{国家代码}/crf.model
"""

from __future__ import annotations

import re

import pycrfsuite

from .markets import MARKETS
from .parse import (HOUSE_NO, NUMBER_MARKERS, UNIT_WORDS, Parsed, Span, city_words, generic_name, region_words,
                    strip_noise)
from .reference import MarketReference
from .text import MARKET_LANG, TYPE_WORDS, core_key, fold, key, norm_postcode, script_of, skeleton, tokenize

SEP = re.compile(r"[,;\n|،]+")


def tokenize_with_sep(text: str, market: str | None = None) -> tuple[list[str], list[bool]]:
    toks, seps = [], []
    for chunk in SEP.split(text):
        t = tokenize(chunk, market)
        toks += t
        seps += [True] + [False] * (len(t) - 1) if t else []
    return toks, seps


def _shape(t: str) -> str:
    s = re.sub(r"[A-Z]", "X", t)
    s = re.sub(r"\d", "d", s)
    s = re.sub(r"[^\sXd/\-]", "x", s)
    return re.sub(r"(.)\1+", r"\1\1", s)[:8]


class Vocab:
    """道路 / 片区 / 楼宇名称里出现过的词，作为特征（相当于"这个词像不像路名"）。"""

    def __init__(self, ref: MarketReference):
        self.street = {w for k in ref.street_keys for w in k.split()}
        self.area = {w for k in ref.area_keys for w in k.split()}
        self.poi = {w for k in (ref.poi_fuzzy.keys if ref.poi_fuzzy else []) for w in k.split()}
        lang = MARKET_LANG.get(ref.market, "EN")
        self.types = TYPE_WORDS.get(lang, set()) | TYPE_WORDS.get("EN", set())
        self.area_types = TYPE_WORDS["AREA"]


def features(tokens: list[str], seps: list[bool], vocab: Vocab) -> list[dict]:
    feats = []
    n = len(tokens)
    for i, t in enumerate(tokens):
        f = {"bias": 1.0, "w": t, "shape": _shape(t), "script": script_of(t), "len": min(len(t), 10) // 3,
             "digit": t.isdigit(), "houseno": bool(HOUSE_NO.match(t)), "slash": "/" in t,
             "pre3": t[:3], "suf3": t[-3:], "sep": seps[i], "first": i == 0, "last": i == n - 1,
             "pos": min(int(4 * i / max(n, 1)), 3),
             "v_street": t in vocab.street, "v_area": t in vocab.area, "v_poi": t in vocab.poi,
             "type": t in vocab.types, "area_type": t in vocab.area_types, "unit": t in UNIT_WORDS,
             "marker": t in NUMBER_MARKERS}
        for d in (-2, -1, 1, 2):
            j = i + d
            if 0 <= j < n:
                u = tokens[j]
                f.update({f"{d}:w": u, f"{d}:shape": _shape(u), f"{d}:v_street": u in vocab.street,
                          f"{d}:v_area": u in vocab.area, f"{d}:type": u in vocab.types,
                          f"{d}:area_type": u in vocab.area_types, f"{d}:unit": u in UNIT_WORDS,
                          f"{d}:marker": u in NUMBER_MARKERS, f"{d}:sep": seps[j]})
            else:
                f[f"{d}:none"] = True
        feats.append({k: (1.0 if v is True else 0.0 if v is False else v) for k, v in f.items()})
    return feats


def train(ref: MarketReference, samples, path, iterations: int = 80) -> None:
    vocab = Vocab(ref)
    tr = pycrfsuite.Trainer(verbose=False)
    for s in samples:
        tr.append(features(s.tokens, s.seps, vocab), s.labels)
    tr.set_params({"c1": 0.05, "c2": 0.01, "max_iterations": iterations, "feature.possible_transitions": True})
    tr.train(str(path))


class CRFParser:
    name = "crf"

    def __init__(self, ref: MarketReference):
        self.ref = ref
        self.m = MARKETS[ref.market]
        self.vocab = Vocab(ref)
        self.tagger = pycrfsuite.Tagger()
        self.tagger.open(str(ref.dir / "crf.model"))
        self.pc_re = re.compile(self.m.postcode) if self.m.postcode else None
        self.neutral = {key(x, ref.market) for x in region_words(ref.market) + city_words(ref.market)}

    def tag(self, text: str) -> tuple[list[str], list[str]]:
        toks, seps = tokenize_with_sep(text, self.ref.market)
        if not toks:
            return [], []
        return toks, self.tagger.tag(features(toks, seps, self.vocab))

    def parse(self, raw: str) -> Parsed:
        text, noise, codes = strip_noise(raw)
        toks, labels = self.tag(text)
        p = Parsed(raw=raw, tokens=toks, codes=codes, noise=noise, parser="crf")
        spans: list[tuple[str, int, int]] = []
        for i, lab in enumerate(labels):
            if spans and spans[-1][0] == lab and spans[-1][2] == i:
                spans[-1] = (lab, spans[-1][1], i + 1)
            else:
                spans.append((lab, i, i + 1))
        for lab, a, b in spans:
            words = " ".join(toks[a:b])
            if key(words, self.ref.market) in self.neutral:
                continue  # 国家 / 大区 / 全城名：不作片区证据（与规则解析一致）
            if lab == "PC" and self.pc_re and self.pc_re.search(fold(words)):
                pc = norm_postcode(self.pc_re.search(fold(words)).group(0), self.ref.market)
                p.postcode = pc if pc.strip("0") else p.postcode
            elif lab == "NUM" and p.number is None and re.search(r"\d", words):
                p.number = toks[b - 1] if HOUSE_NO.match(toks[b - 1]) else words
            elif lab == "UNIT":
                p.unit = words.rstrip("/")
            elif lab == "STREET":
                p.streets += self._lookup(words, a, b, "street")
            elif lab == "AREA":
                p.areas += self._lookup(words, a, b, "area")
            elif lab == "BLDG" and self.ref.poi_fuzzy is not None:
                k = key(words, self.ref.market)
                for hit, score, ids in self.ref.poi_fuzzy.search(k, limit=2, min_score=88):
                    if len(ids) <= 20 and not generic_name(hit):
                        p.buildings.append(Span(hit, a, b, ids, score, "exact" if score == 100 else "fuzzy"))
        if self.ref.market == "AU" and p.unit is None:  # 5/12 形式
            for t in toks:
                m = re.fullmatch(r"(\d+[A-Z]?)/(\d+[A-Z]?)", t)
                if m and p.number == t:
                    p.unit, p.number = f"UNIT {m.group(1)}", m.group(2)
        p.streets.sort(key=lambda s: -s.score)
        return p

    def _lookup(self, words: str, a: int, b: int, kind: str) -> list[Span]:
        """把 CRF 标出的片段到参考库里找：完整键 -> 核心键 -> 容错检索。"""
        table = self.ref.street_keys if kind == "street" else self.ref.area_keys
        index = self.ref.street_fuzzy if kind == "street" else self.ref.area_fuzzy
        k = " ".join(key(words, self.ref.market).split())
        if k in table:
            return [Span(k, a, b, sorted(table[k]), 100.0, "exact")]
        ck = core_key(words, self.ref.market, kind)
        core = self.ref.street_core if kind == "street" else self.ref.area_core
        if ck in core and len(ck) >= 4 and not (kind == "street" and ck in self.ref.area_keys):
            return [Span(ck, a, b, sorted(core[ck]), 97.0, "core")]
        out = []
        if index is not None and len(k) >= 4:
            for cand in {k, ck}:
                for hit, score, ids in index.search(cand, limit=2, min_score=84):
                    if re.findall(r"\d+", hit) == re.findall(r"\d+", cand):  # 数字不做容错
                        out.append(Span(hit, a, b, ids, score, "fuzzy"))
        skel = getattr(self.ref, "street_skel" if kind == "street" else "area_skel", None)
        if not out and skel:  # 阿拉伯文市场：拉丁转写 <-> 阿拉伯文
            sk = skeleton(words)
            if len(sk) >= (4 if kind == "street" else 3) and sk in skel and len(skel[sk]) <= 30:
                out.append(Span(sk, a, b, sorted(skel[sk]), 90.0, "translit"))
        return sorted(out, key=lambda s: -s.score)[:3]
