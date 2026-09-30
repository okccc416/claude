"""地址参考库：加载 + 多路索引（邮编 / 楼栋+道路 / 道路 / 楼宇名）。"""

from __future__ import annotations

import csv
import gzip
import io
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from rapidfuzz import fuzz, process
from rapidfuzz.distance import Levenshtein

from .normalize import ROAD_TYPE_WORDS, match_key, split_alpha_num

# 楼宇名里代表"片区"而非单栋楼的词
_AREA_WORDS = ("ESTATE", "CONSERVATION AREA", "EST")
_TYPE_WORDS = list(ROAD_TYPE_WORDS)


@dataclass
class Entity:
    eid: int
    blk: str
    road: str  # 参考库原始道路名（大写全称）
    road_key: str
    postal: str
    buildings: list[str]
    lat: float
    lng: float

    @property
    def is_hdb(self) -> bool:
        """组屋邮编规则：2 位邮区 + 1 位字母后缀编码（A=1…）+ 3 位楼号，如 Blk 655C -> 823655。组屋一定是多单元楼。"""
        m = re.fullmatch(r"(\d{1,3})([A-H]?)", self.blk)
        if not m or len(self.postal) != 6:
            return False
        return self.postal[3:] == m.group(1).zfill(3) and self.postal[2] == (
            "0" if not m.group(2) else str(ord(m.group(2)) - 64))

    @property
    def primary_building(self) -> str | None:
        """仅当该地址只有一个楼宇名且不是片区名时返回（OneMap 的"楼宇名"多为楼内商户 / POI）。"""
        if len(self.buildings) == 1 and not any(w in self.buildings[0] for w in _AREA_WORDS):
            return self.buildings[0]
        return None


@dataclass
class RoadMatch:
    key: str
    start: int
    end: int
    score: float  # 100 = 规范键完全一致
    exact: bool


@dataclass
class ReferenceDB:
    entities: list[Entity] = field(default_factory=list)
    by_postal: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))
    by_blk_road: dict[tuple[str, str], list[int]] = field(default_factory=lambda: defaultdict(list))
    by_road: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))
    road_display: dict[str, str] = field(default_factory=dict)
    by_building: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))
    # 道路按"数字部分"分组，模糊匹配只在数字完全相同的道路之间进行
    _road_groups: dict[tuple[str, ...], tuple[list[str], list[str]]] = field(default_factory=dict)
    _building_keys: list[str] = field(default_factory=list)
    _building_tokens: dict[str, set[int]] = field(default_factory=lambda: defaultdict(set))
    vocab: set[str] = field(default_factory=set)  # 参考库中出现过的全部词
    _spell_words: list[str] = field(default_factory=list)  # 路名用词（按出现频次降序），用于逐词拼写纠错
    _spell_map: dict[str, str] = field(default_factory=dict)
    # 可选：楼栋属性（如最高楼层），用于单元号校验
    max_floor_by_postal: dict[str, int] = field(default_factory=dict)

    # ---------- 构建 ----------
    @classmethod
    def from_rows(cls, rows) -> "ReferenceDB":
        db = cls()
        for row in rows:
            buildings = [b for b in (row.get("buildings") or "").split("|") if b and b != "NIL"]
            e = Entity(
                eid=len(db.entities),
                blk=row["blk"].strip().upper(),
                road=row["road"].strip().upper(),
                road_key=match_key(row["road"]),
                postal=row["postal"].strip(),
                buildings=buildings,
                lat=float(row.get("lat") or 0),
                lng=float(row.get("lng") or 0),
            )
            db._add(e)
        db._finalize()
        return db

    @classmethod
    def load(cls, path: str | Path) -> "ReferenceDB":
        path = Path(path)
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8", newline="") as f:
            return cls.from_rows(csv.DictReader(f))

    def load_building_attributes(self, path: str | Path) -> None:
        """可选的楼栋属性表（CSV：postal,max_floor），如 HDB 楼栋最高楼层。"""
        with open(path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("max_floor"):
                    self.max_floor_by_postal[row["postal"].strip()] = int(row["max_floor"])

    def _add(self, e: Entity) -> None:
        self.entities.append(e)
        self.by_postal[e.postal].append(e.eid)
        self.by_blk_road[(e.blk, e.road_key)].append(e.eid)
        self.by_road[e.road_key].append(e.eid)
        self.road_display.setdefault(e.road_key, e.road)
        for b in e.buildings:
            key = match_key(b)
            self.by_building[key].append(e.eid)
            for t in key.split():
                self._building_tokens[t].add(e.eid)

    def _finalize(self) -> None:
        groups: dict[tuple[str, ...], tuple[list[str], list[str]]] = {}
        for key in self.by_road:
            alpha, nums = split_alpha_num(key)
            g = groups.setdefault(nums, ([], []))
            g[0].append(alpha)
            g[1].append(key)
        self._road_groups = groups
        self._building_keys = list(self.by_building)
        self.vocab = {t for k in self.by_road for t in k.split()} | set(self._building_tokens)
        freq: dict[str, int] = defaultdict(int)
        for k, ids in self.by_road.items():
            for t in k.split():
                if t.isalpha() and len(t) >= 3:
                    freq[t] += len(ids)
        self._spell_map = {t: t for t in freq}
        self._spell_map.update({full: canon for full, canon in ROAD_TYPE_WORDS.items()})
        self._spell_words = sorted(self._spell_map, key=lambda t: -freq.get(t, 10 ** 9))

    def remove(self, eids: set[int]) -> "ReferenceDB":
        """返回去掉部分实体后的新库（用于模拟参考数据过时 / 不完整）。"""
        rows = [
            {
                "blk": e.blk, "road": e.road, "postal": e.postal,
                "buildings": "|".join(e.buildings), "lat": e.lat, "lng": e.lng,
            }
            for e in self.entities if e.eid not in eids
        ]
        return ReferenceDB.from_rows(rows)

    # ---------- 查询 ----------
    def fix_type_typos(self, tokens: list[str]) -> list[str]:
        """纠正路型词本身的拼写错误（AENUE -> AVE、CRECSENT -> CRES）。

        参考库里出现过的词一律不动，避免把真实地名（如 PALACE）"纠正"成路型词。
        """
        out = []
        for t in tokens:
            if len(t) >= 4 and t.isalpha() and t not in self.vocab:
                hit = process.extractOne(t, _TYPE_WORDS, scorer=fuzz.ratio, score_cutoff=80)
                if hit:
                    out.append(ROAD_TYPE_WORDS[hit[0]])
                    continue
            out.append(t)
        return out

    def spell_fix(self, tokens: list[str]) -> list[str]:
        """逐词拼写纠错（针对多处拼写错误）：参考库里没有的词，改成编辑距离最近的路名用词。

        距离上限：≤5 个字母允许 1 处，更长允许 2 处；距离相同取更常见的词。只作为备选切分，由打分裁决。
        """
        out = []
        for t in tokens:
            if len(t) >= 4 and t.isalpha() and t not in self.vocab:
                hit = process.extractOne(t, self._spell_words, scorer=Levenshtein.distance,
                                         score_cutoff=1 if len(t) <= 5 else 2)
                if hit:
                    out.append(self._spell_map[hit[0]])
                    continue
            out.append(t)
        return out

    def find_roads(self, tokens: list[str], fuzzy: bool = True, top: int = 5,
                   max_span: int = 7, min_score: float = 85) -> list[RoadMatch]:
        """在 token 序列的所有连续片段中寻找道路名；数字部分必须精确一致，字母部分允许拼写误差。"""
        found: dict[str, RoadMatch] = {}
        n = len(tokens)
        for i in range(n):
            if any(c.isdigit() for c in tokens[i]):
                continue
            for j in range(i + 1, min(n, i + max_span) + 1):
                span = " ".join(tokens[i:j])
                if span in self.by_road:
                    cands = [RoadMatch(span, i, j, 100.0, True)]
                elif fuzzy:
                    alpha, nums = split_alpha_num(span)
                    group = self._road_groups.get(nums)
                    if not group or len(alpha) < 4:
                        continue
                    # 取前 3 个：拼写错误常与多条真路名等距（POXLE -> POOLE / OXLEY），留给楼栋号裁决
                    hits = process.extract(alpha, group[0], scorer=fuzz.ratio, score_cutoff=min_score, limit=3)
                    cands = [RoadMatch(group[1][h[2]], i, j, float(h[1]), False) for h in hits]
                else:
                    continue
                for cand in cands:
                    prev = found.get(cand.key)
                    if prev is None or (cand.score, cand.end - cand.start) > (prev.score, prev.end - prev.start):
                        found[cand.key] = cand
        ranked = sorted(found.values(), key=lambda m: (m.score, m.end - m.start), reverse=True)
        return ranked[:top]

    def exact_building(self, tokens: list[str], suffix: list[str] | None = None,
                       prefix: list[str] | None = None) -> list[int]:
        """楼宇名精确命中；可带上被剔除的首尾国家名再试（UNIVERSAL STUDIOS SINGAPORE、SINGAPORE MANAGEMENT UNIVERSITY）。"""
        pre, suf = prefix or [], suffix or []
        for toks in ([*pre, *tokens, *suf], [*tokens, *suf], [*pre, *tokens], tokens):
            if toks:
                key = " ".join(toks)
                if key in self.by_building:
                    return sorted(set(self.by_building[key]))
        return []

    def find_building_entities(self, tokens: list[str], min_score: float = 90, fuzzy: bool = True,
                               suffix: list[str] | None = None) -> list[int]:
        """楼宇名 / POI 检索：精确命中 > 所有词都出现在某个楼宇名中（AND 语义）> 整串模糊匹配。"""
        key = " ".join(tokens)
        if not key:
            return []
        exact = self.exact_building(tokens, suffix)
        if exact:
            return exact
        sets = [self._building_tokens.get(t) for t in tokens]
        if all(sets):
            hit = set.intersection(*sets)
            if hit:
                return sorted(hit)
        if not fuzzy:
            return []
        hits = process.extract(key, self._building_keys, scorer=fuzz.token_sort_ratio,
                               score_cutoff=min_score, limit=5)
        return sorted({e for h in hits for e in self.by_building[h[0]]})

    def road_centroid(self, road_key: str) -> tuple[float, float]:
        ids = self.by_road.get(road_key) or []
        if not ids:
            return (0.0, 0.0)
        lat = sum(self.entities[i].lat for i in ids) / len(ids)
        lng = sum(self.entities[i].lng for i in ids) / len(ids)
        return (lat, lng)


def rows_from_onemap_dump(records) -> list[dict]:
    """把 OneMap 导出（buildings.json）按 (楼栋号, 道路, 邮编) 聚合为地址实体。"""
    agg: dict[tuple[str, str, str], dict] = {}
    for r in records:
        blk, road, postal = r["BLK_NO"].strip(), r["ROAD_NAME"].strip(), r["POSTAL"].strip()
        if not blk or blk == "NIL" or not road or road == "NIL" or len(postal) != 6:
            continue
        key = (blk, road, postal)
        item = agg.setdefault(key, {"blk": blk, "road": road, "postal": postal, "buildings": [],
                                    "lat": r["LATITUDE"], "lng": r["LONGITUDE"]})
        b = r.get("BUILDING", "").strip()
        if b and b != "NIL" and b not in item["buildings"]:
            item["buildings"].append(b)
    rows = []
    for item in agg.values():
        item["buildings"] = "|".join(item["buildings"])
        rows.append(item)
    return rows


def write_rows(rows: list[dict], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["blk", "road", "postal", "buildings", "lat", "lng"])
    w.writeheader()
    w.writerows(rows)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(buf.getvalue())
