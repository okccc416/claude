"""新加坡地址校验（Address Validation）MVP。"""

from .reference import ReferenceDB
from .validator import Config, Validator

__all__ = ["Config", "ReferenceDB", "Validator"]
