"""试点范围守卫：输入写的城镇 / 邮编 / 一级行政区都在试点范围外（且没有任何一项在范围内）时，不再拿试点城市里的
同名道路去匹配——参考库里根本没有这条地址，匹配上的只会是另一座城市的同名路。

依据全国地名 / 邮编表（GeoNames，scripts/fetch_gazetteer.py 生成 data/markets/<市场>/gazetteer.json.gz）：
  范围内证据  邮编在参考库里（或全国邮编表里的位置在范围内）；某一段在地名表里有一处城镇落在试点范围内；
             某一段正好是参考库片区名（片区中心在试点范围内）/ 城区片区名
  范围外证据  邮编在全国邮编表里、位置在试点范围外；某一段在地名表里只有范围外的城镇；
             某一段是一级行政区名（州 / 省），而试点范围不在这个行政区里
只用整段（逗号分隔的一段，去掉邮编、门牌数字、州缩写）与地名完全一致作证据；证据按具体程度打分，见 assess。
"""

from __future__ import annotations

import gzip
import json
import math
import pickle
import re
import unicodedata
from dataclasses import dataclass, field

from .markets import MARKETS
from .parse import AU_STATES, city_words, region_words
from .reference import MarketReference, haversine
from .noise import strip_noise
from .text import TYPE_WORDS, fold, key, norm_postcode, type_words

VERSION = 3  # 索引格式 / 规范化方式变了就加一，缓存自动重建
MARGIN_DEG = 0.03  # 试点范围向外放宽约 3 公里（边界附近的城镇，参考库里可能有它的一部分道路）
_SEG = re.compile(r"\s*(?:[,;|\n]|\s[-–—]\s)\s*")
_PARTICLES = {"DE", "DA", "DO", "DAS", "DOS", "DEL", "DI", "DU", "LA", "LE", "EL", "AL", "VON", "VAN", "DER", "DEN", "THE"}


def norm(s: str) -> str:
    """地名比较键：统一写法后只留字母、数字和组合符号（Glienicke/Nordbahn = GLIENICKE NORDBAHN；泰文的元音符号保留）。"""
    return " ".join("".join(c if unicodedata.category(c)[0] in "LNM" else " " for c in fold(s)).split())


@dataclass
class Coverage:
    status: str  # INSIDE / OUTSIDE / UNKNOWN
    inside: list[str] = field(default_factory=list)
    outside: list[str] = field(default_factory=list)
    place: str | None = None  # 范围外最可能的城镇（或邮编所在地）
    lat: float | None = None
    lng: float | None = None
    points: list[tuple] = field(default_factory=list)  # 范围外证据的位置 (纬度, 经度, 半径米)：所写城镇的各处同名地点、邮编位置


class Gazetteer:
    def __init__(self, ref: MarketReference):
        self.ref = ref
        self.market = ref.market
        self.m = MARKETS[ref.market]
        self.boxes = [(b[0] - MARGIN_DEG, b[1] - MARGIN_DEG, b[2] + MARGIN_DEG, b[3] + MARGIN_DEG)
                      for _, b in self.m.regions]
        self.names: dict[str, list[tuple]] = {}  # 键 -> [(纬度, 经度, 类别, 人口, 一级行政区, 名称)]
        self.postcodes: dict[str, list[tuple]] = {}  # 规范化邮编 -> [(纬度, 经度, 地名)]
        self.pc_lens: list[int] = []
        self.pilot_admin1: set[str] = set()
        self.cities: list[tuple] = []  # 人口 1.5 万以上的城镇 (纬度, 经度, 人口, 各语种名称)：响应里补全城市名（google.py）
        self.ok = self._load()
        self.neutral = {norm(w) for w in region_words(self.market)}
        self.city = {norm(w) for w in city_words(self.market)} | {norm(c) for c in self.m.cities}
        self.pc_re = re.compile(self.m.postcode) if self.m.postcode else None

    # ------------------------------------------------------------------ 载入
    def _load(self) -> bool:
        src = self.ref.dir / "gazetteer.json.gz"
        cache = self.ref.dir / "gazetteer.idx.pkl"
        if not src.exists():
            return False
        if cache.exists() and cache.stat().st_mtime >= src.stat().st_mtime:
            try:
                with open(cache, "rb") as f:
                    d = pickle.load(f)
                if d.get("v") == VERSION:
                    self.names, self.postcodes, self.pc_lens, self.pilot_admin1, self.cities = (
                        d["names"], d["postcodes"], d["pc_lens"], d["pilot_admin1"], d["cities"])
                    return True
            except Exception:  # noqa: BLE001  缓存损坏：重建
                pass
        with gzip.open(src, "rt", encoding="utf-8") as f:
            raw = json.load(f)
        self._build(raw)
        try:
            with open(cache, "wb") as f:
                pickle.dump({"v": VERSION, "names": self.names, "postcodes": self.postcodes,
                             "pc_lens": self.pc_lens, "pilot_admin1": self.pilot_admin1, "cities": self.cities}, f)
        except OSError:  # 只读部署目录：每次启动重建
            pass
        return True

    def _build(self, raw: dict) -> None:
        names: dict[str, list[tuple]] = {}
        for nms, lat, lng, kind, pop, a1 in raw["places"]:
            if kind == "P" and pop > 0 and self.in_pilot(lat, lng):
                self.pilot_admin1.add(a1)
            entry = (lat, lng, kind, pop, a1, nms[0])
            if kind == "P" and pop >= 15000:
                self.cities.append((lat, lng, pop, nms))
            for k in {norm(n) for n in nms}:
                if len(k) >= 3 and not k.isdigit():
                    names.setdefault(k, []).append(entry)
        # 同名地点太多的键（Centro、San José 一类）只保留人口最大的几处 + 范围内的全部
        for k, v in names.items():
            if len(v) > 40:
                v.sort(key=lambda e: -e[3])
                names[k] = v[:40] + [e for e in v[40:] if self.in_pilot(e[0], e[1])]
        self.names = names
        if self.m.postcode:
            for pc, place, lat, lng in raw["postcodes"]:
                k = norm_postcode(pc, self.market)
                if k:
                    self.postcodes.setdefault(k, []).append((lat, lng, place))
            self.pc_lens = sorted({len(k) for k in self.postcodes}, reverse=True)

    def in_pilot(self, lat: float, lng: float) -> bool:
        return any(b[0] <= lng <= b[2] and b[1] <= lat <= b[3] for b in self.boxes)

    def where(self, lat: float, lng: float, pop: int, r: float | None = None) -> int:
        """城镇与试点范围：2 = 中心在范围内；1 = 中心在外但城区跨进范围（按人口估的城区半径）；0 = 范围外。"""
        if self.in_pilot(lat, lng):
            return 2
        r = r or 3000.0 + 2000.0 * math.log10(max(pop, 1000) / 1000)
        for b in self.boxes:
            clat, clng = min(max(lat, b[1]), b[3]), min(max(lng, b[0]), b[2])
            if haversine(lat, lng, clat, clng) <= r:
                return 1
        return 0

    def _area_in(self, k: str, min_radius: float = 0.0) -> bool:
        """参考库里有这个片区名、而且是试点范围里的片区（中心在范围内，或边界跨进范围的区县；不含整个州）。
        min_radius：只算有边界、半径至少这么大的片区（区县级）。"""
        ref = self.ref
        return any((self.in_pilot(a.lat, a.lng) or (a.has_poly and a.radius_m <= 15000))
                   and (not min_radius or (a.has_poly and a.radius_m >= min_radius))
                   for a in (ref.areas[i] for i in ref.area_keys.get(k, ())))

    # ------------------------------------------------------------------ 判断
    def _postcode_place(self, pc: str) -> list[tuple] | None:
        if pc in self.postcodes:
            return self.postcodes[pc]
        if self.market == "BR" and len(pc) == 8 and pc[:5] + "000" in self.postcodes:  # 小城镇整城一个邮编
            return self.postcodes[pc[:5] + "000"]
        if self.market == "GB" and len(pc) >= 5 and pc[:-3] in self.postcodes:  # 只有外码（SW1A）
            return self.postcodes[pc[:-3]]
        for n in self.pc_lens:  # 加拿大 FSA、爱尔兰路由码、荷兰 4 位数字
            if n < len(pc) and self.market in ("CA", "IE", "NL") and pc[:n] in self.postcodes:
                return self.postcodes[pc[:n]]
        return None

    def _candidates(self, text: str, street: str | None = None) -> list[tuple[str, float]]:
        """每一段去掉邮编、州缩写后的文字（只取整段，不在段内找词），以及这一段能作多少范围外证据（权重系数）：
          第一段（道路 / 店名 / 楼名）、去掉邮编后还带数字或道路类型词的段、就是引擎匹配上的那条路的段
          （Uspallata、Nguyễn Trãi：拉美 / 越南道路常以城镇、人名命名）不作范围外证据（0）；
          第一个带数字的段之前的段减半（多半是店名 / 片区名）。
        城镇和州写在同一段（Marl Nordrhein-Westfalen）时，去掉末尾的州名再查一次；LOCALIDAD KENNEDY、
        Glienicke/Nordbahn 去掉片区类型词 / 斜杠后半再查一次。"""
        out: list[tuple[str, float]] = []
        seen_digit = False
        types = {t for t in type_words(self.market) if len(t) >= 3 and t not in _PARTICLES}
        parts = re.split(f"({_SEG.pattern})", fold(strip_noise(text, self.ref)[0]))  # 先去掉收件人、公司、备注等
        segs, dash = parts[0::2], [False] + [bool(re.search(r"[-–—]", x)) for x in parts[1::2]]
        for i, seg in enumerate(segs):
            s = self.pc_re.sub(" ", seg) if self.pc_re else seg  # 去掉邮编
            ks = key(s, self.market)
            streetish = bool(re.search(r"\d", s)) or bool(set(ks.split()) & types) or bool(
                street and (ks == street or (len(street) >= 5 and f" {street} " in f" {ks} ")
                            # 路名本身带" - "（Carretera Bayamón - Aguas Buenas）：后半段是路名的一部分
                            or (dash[i] and len(ks) >= 5 and f" {ks} " in f" {street} ")))
            w = 0.0 if i == 0 or streetish else 0.5 if not seen_digit else 1.0
            seen_digit = seen_digit or bool(re.search(r"\d", seg))
            toks = norm(s).split()
            if self.market == "AU":
                toks = [t for t in toks if t not in AU_STATES]
            toks = [t for t in toks if not t.isdigit()]
            k = " ".join(toks)
            if len(k) < 3 or any(k == c for c, _ in out):
                continue
            out.append((k, w))
            if k in self.names or k in self.neutral or k in self.ref.area_keys:
                continue
            core = " ".join(t for t in toks if t not in TYPE_WORDS["AREA"])  # LOCALIDAD KENNEDY -> KENNEDY
            if core != k and len(core) >= 3:
                out.append((core, w))
                continue
            first = " ".join(t for t in norm(re.split(r"[/(]", s)[0]).split() if not t.isdigit())  # Glienicke/Nordbahn
            if first != k and len(first) >= 3:
                out.append((first, w))
                continue
            for j in range(1, len(toks)):  # 城镇 + 州：城镇本身也要是已知地名
                head, tail = " ".join(toks[:j]), " ".join(toks[j:])
                if (tail in self.neutral or any(h[2] == "A1" for h in self.names.get(tail, ()))) \
                        and (head in self.names or head in self.ref.area_keys):
                    out += [(head, w), (tail, w)]
                    break
        return out

    def assess(self, text: str, postcode: str | None, street: str | None = None) -> Coverage:
        """逐段给证据打分，范围外的分数高于范围内才判 OUTSIDE（越具体的证据分越高）：
          邮编 3；城镇 2（人口不详的小村 0.5；权重系数见 _candidates）；参考库片区名 / 城区片区 / 既是试点城市又是所在州的
          名称 1；范围外的州 1；国家 / 州 / 全城名 0.5。
        同一段既有范围内又有范围外的同名地点时算范围内，除非范围外那处是大城市而范围内只是同名小村（Porto）。"""
        if not self.ok:
            return Coverage("UNKNOWN")
        ref = self.ref
        cov = Coverage("UNKNOWN")
        score_in = score_out = 0.0
        outs: list[tuple] = []  # (具体程度, 人口, 纬度, 经度, 名称)：邮编所在地 > 城镇 > 一级行政区
        named_out = False
        if postcode:
            known = ref.postcodes.get(postcode)
            hits = self._postcode_place(postcode)
            where = max((self.where(h[0], h[1], 0, 8000.0) for h in hits), default=-1) if hits else -1
            # 参考库邮编表来自官方地址表（pc_complete）或有 10 条以上地址时以参考库为准；只有零星几条（取自商户地址，
            # 吉隆坡的商户写了槟城邮编）而全国邮编表说在范围外时，两边矛盾，不作证据
            if known and (ref.pc_complete or known[2] >= 10 or where == -1):
                cov.inside.append(f"postcode:{postcode}")
                score_in += 3 if (ref.pc_complete or known[2] >= 3) else 1
            elif where == 2:
                cov.inside.append(f"postcode:{postcode}")
                score_in += 3
            elif where == 0 and not known:  # 邮编区（加拿大 FSA、英国外码）中心在边界外几公里内的不算范围外
                cov.outside.append(f"postcode:{postcode}")
                score_out += 3
                outs.append((3, 0, hits[0][0], hits[0][1], hits[0][2]))
                cov.points += [(h[0], h[1], 15000.0) for h in hits]
        for k, w in self._candidates(text, street):
            hits = self.names.get(k, [])
            towns_in, towns_part, towns_out = [], [], []
            in_ref = k in ref.area_keys  # 参考库有这个片区名：跨进试点范围的区县，大片区的中心不能说明在范围外
            for h in hits:  # 居民点；城区片区（澳洲的 suburb）和二三级行政区（奥地利的 Gemeinde）只在范围外时当城镇
                if h[2] in ("P", "X", "A2", "A3") and (h[2] == "P" or not in_ref):
                    where = self.where(h[0], h[1], h[3])
                    if h[2] == "P" or where == 0:
                        (towns_in if where == 2 else towns_part if where == 1 else towns_out).append(h)
            a1 = [h for h in hits if h[2] == "A1"]
            a1_pilot = any(h[4] in self.pilot_admin1 for h in a1)
            if k in self.neutral or k in self.city:  # 国家 / 州 / 全城名：最多是弱的范围内证据（常是州名，不说明在城里）
                if towns_in or a1_pilot:
                    cov.inside.append(f"city:{k}")
                    score_in += 0.5
                continue
            if a1_pilot and not towns_in:  # 试点所在的州（Brandenburg 不是勃兰登堡市）：不作证据
                continue
            big_out = max((h[3] for h in towns_out), default=0)
            small_in = max((h[3] for h in towns_in + towns_part), default=0)
            # 小片区与范围外的大城市同名（波哥大的 Santa Marta、墨西哥城的 Puebla 区）不作范围内证据；
            # 区县级的片区（东京的江東区，GeoNames 里另有同名的外地城市）、参考库和 GeoNames 都在范围内的片区
            #（雅加达的 Grogol）照算
            gaz_in = any(h[2] in ("X", "A2", "A3") and self.in_pilot(h[0], h[1]) for h in hits)
            ref_in = self._area_in(k)
            area_in = self._area_in(k, 2000.0) or (ref_in and (gaz_in or bool(towns_in))) or (
                big_out < 100000 and (ref_in or gaz_in))
            if towns_in and not (big_out >= 10000 and small_in * 20 < big_out and not area_in):
                cov.inside.append(f"place:{k}")
                score_in += 1 if a1_pilot else 2  # Berlin / Madrid / Auckland：既是城市也是州，写的可能是州
                continue
            if area_in or (towns_part and not (big_out >= 10000 and small_in * 20 < big_out)):
                cov.inside.append(f"area:{k}")  # 参考库片区 / 跨在试点边界上的城镇（Tláhuac）/ 城区片区
                score_in += 1
                continue
            if towns_out and w > 0:
                cov.outside.append(f"place:{k}")
                h = max(towns_out, key=lambda e: e[3])
                score_out += (2 if h[3] >= 1000 else 0.5) * w  # 人口不详的小村常与普通词、城区片区同名（Gracias、El Cinco）
                outs.append((2, h[3], h[0], h[1], h[5]))
                big = [e for e in towns_out if e[3] >= max(1000, h[3] * 0.05)] or sorted(towns_out, key=lambda e: -e[3])[:5]
                cov.points += [(e[0], e[1], town_radius(e[3])) for e in big]  # 同名小村太多时只看像样的城镇
                named_out = named_out or w > 0
            elif a1 and not a1_pilot and not towns_out and w > 0:
                cov.outside.append(f"region:{k}")
                score_out += w
                h = max(a1, key=lambda e: e[3])
                outs.append((1, h[3], h[0], h[1], h[5]))
                named_out = named_out or w > 0
        # 写了范围内的城镇 / 片区，范围外的只有邮编：多半是邮编写错（引擎自己会核对邮编），不判范围外
        if score_out > score_in and (named_out or not cov.inside):
            cov.status = "OUTSIDE"
            _, _, cov.lat, cov.lng, cov.place = max(outs)  # 位置：邮编所在地 > 城镇 > 州
            towns = [o for o in outs if o[0] == 2]
            if towns:  # 名称用所写的城镇（邮编表里的地名常是城区名）
                cov.place = max(towns)[4]
        elif cov.inside:
            cov.status = "INSIDE"
        return cov


def town_radius(pop: int) -> float:
    """城镇的大致半径（米）：小镇 8 公里，百万人口约 20 公里，最大 30 公里。"""
    return min(30000.0, max(8000.0, 8000.0 + 4000.0 * math.log10(max(pop, 1) / 1000)))


def locality_check(cov: Coverage, lat: float, lng: float) -> str:
    """范围外的地址：geo 返回的点在不在所写城镇 / 邮编附近。CONFIRMED / CONFLICT / ""（只写了州，无从核对）。"""
    if not cov.points:
        return ""
    return "CONFIRMED" if any(haversine(lat, lng, a, b) <= r for a, b, r in cov.points) else "CONFLICT"


def gazetteer(ref: MarketReference) -> Gazetteer:
    g = ref.__dict__.get("_gazetteer")
    if g is None:
        g = ref.__dict__["_gazetteer"] = Gazetteer(ref)
    return g
