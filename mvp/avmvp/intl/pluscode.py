"""Plus Code（Open Location Code）解码：把 `8FVC9G8F+6X` 或短码 `JP63+MM, Riyadh` 还原成坐标。

算法按公开规范（github.com/google/open-location-code 的 specification）实现：
  前 10 位：纬度 / 经度交替，每对的精度依次为 20°、1°、0.05°、0.0025°、0.000125°
  第 11 位起：网格细分，每位把格子分成 5 行 x 4 列
  短码（"+" 前不足 8 位）：用参考位置补齐前缀，再选离参考位置最近的那一格
中东、东南亚很多商户用 Plus Code 代替门牌（见 docs/12），解码后可以直接定位到约 14 米见方的格子。
"""

from __future__ import annotations

ALPHABET = "23456789CFGHJMPQRVWX"
_PAIR_RES = [20.0, 1.0, 0.05, 0.0025, 0.000125]


def _clean(code: str) -> tuple[str, int] | None:
    code = code.strip().upper()
    if code.count("+") != 1:
        return None
    head, tail = code.split("+")
    if not (2 <= len(head) <= 8 and len(head) % 2 == 0) or any(c not in ALPHABET for c in head + tail) \
            or len(tail) == 1:
        return None
    return head + tail, len(head)


def encode(lat: float, lng: float, length: int = 10) -> str:
    lat = min(max(lat, -90.0), 90.0 - 1e-10) + 90.0
    lng = (lng + 180.0) % 360.0
    out = ""
    for res in _PAIR_RES[: length // 2]:
        d_lat, d_lng = int(lat // res), int(lng // res)
        out += ALPHABET[d_lat] + ALPHABET[d_lng]
        lat -= d_lat * res
        lng -= d_lng * res
    return out[:8] + "+" + out[8:]


def decode(code: str) -> tuple[float, float, float] | None:
    """完整码 -> (纬度, 经度, 格子边长约多少米)；短码或非法输入返回 None。"""
    c = _clean(code)
    if c is None or c[1] != 8:
        return None
    digits = c[0]
    lat = lng = 0.0
    lat_res = lng_res = 0.0
    for i, res in enumerate(_PAIR_RES):
        if 2 * i + 1 >= len(digits):
            break
        lat += ALPHABET.index(digits[2 * i]) * res
        lng += ALPHABET.index(digits[2 * i + 1]) * res
        lat_res = lng_res = res
    for ch in digits[10:15]:  # 网格细分
        lat_res, lng_res = lat_res / 5, lng_res / 4
        idx = ALPHABET.index(ch)
        lat += (idx // 4) * lat_res
        lng += (idx % 4) * lng_res
    return lat - 90 + lat_res / 2, lng - 180 + lng_res / 2, lat_res * 111000


def recover(code: str, ref_lat: float, ref_lng: float) -> tuple[float, float, float] | None:
    """短码（如 JP63+MM）按参考位置补齐；完整码直接解码。"""
    c = _clean(code)
    if c is None:
        return None
    head = code.strip().upper().split("+")[0]
    if len(head) == 8:
        return decode(code)
    pad = 8 - len(head)
    full = encode(ref_lat, ref_lng)[:pad] + code.strip().upper()
    res = decode(full)
    if res is None:
        return None
    lat, lng, size = res
    resolution = 20.0 ** (2 - pad / 2)
    half = resolution / 2
    if ref_lat + half < lat and lat - resolution >= -90:
        lat -= resolution
    elif ref_lat - half > lat and lat + resolution <= 90:
        lat += resolution
    if ref_lng + half < lng:
        lng -= resolution
    elif ref_lng - half > lng:
        lng += resolution
    return lat, lng, size
