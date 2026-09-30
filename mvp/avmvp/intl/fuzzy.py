"""字符三元组倒排索引 + rapidfuzz 复核：在几万到几十万个名称里做容错检索（拼错、少字、转写差异）。

对泰文等不用空格分词的文字同样有效（三元组按字符切）。
"""

from __future__ import annotations

from collections import Counter, defaultdict

from rapidfuzz import fuzz


def _grams(s: str) -> set[str]:
    s = f"  {s} "
    return {s[i:i + 3] for i in range(len(s) - 2)}


class FuzzyIndex:
    def __init__(self, entries: dict[str, list[int]]):
        self.keys = list(entries)
        self.ids = [entries[k] for k in self.keys]
        self.pos = {k: i for i, k in enumerate(self.keys)}
        self.index: dict[str, list[int]] = defaultdict(list)
        for i, k in enumerate(self.keys):
            for g in _grams(k):
                self.index[g].append(i)
        # 很常见的三元组（如 "ST "）区分度低，查询时跳过，控制耗时
        self.common = {g for g, v in self.index.items() if len(v) > max(2000, len(self.keys) // 20)}

    def get(self, key: str) -> list[int] | None:
        """完全一致的键 -> 对象编号。"""
        i = self.pos.get(key)
        return None if i is None else self.ids[i]

    def search(self, query: str, limit: int = 5, min_score: float = 80.0) -> list[tuple[str, float, list[int]]]:
        """返回 [(命中的键, 分数 0-100, 对象编号列表)]，按分数从高到低。"""
        if not query:
            return []
        grams = _grams(query) - self.common or _grams(query)
        counts: Counter = Counter()
        for g in grams:
            for i in self.index.get(g, ()):
                counts[i] += 1
        out = []
        for i, _ in counts.most_common(60):
            k = self.keys[i]
            score = fuzz.ratio(query, k)
            if score >= min_score:
                out.append((k, score, self.ids[i]))
        out.sort(key=lambda x: -x[1])
        return out[:limit]
