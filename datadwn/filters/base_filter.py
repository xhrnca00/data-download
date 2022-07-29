from abc import ABCMeta, abstractmethod

from ..util import json_obj


class BaseFilter(metaclass=ABCMeta):
    def __init__(self) -> None:
        # no config (yet?) because no implementors
        # * (this functionality is stage 2)
        pass

    @abstractmethod
    def is_in(self, vehicle: json_obj, image: bytes) -> bool: ...
