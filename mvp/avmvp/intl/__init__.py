"""多市场地址校验：澳洲、欧洲（有开放官方地址表）与中东、东南亚（用地图数据验真）。"""

from .markets import MARKETS, Market

__all__ = ["MARKETS", "Market"]
