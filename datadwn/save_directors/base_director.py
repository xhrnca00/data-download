from abc import ABCMeta, abstractmethod

from ..util import json_obj


class BaseDirector(metaclass=ABCMeta):
    def __init__(self) -> None:
        # base director does not need any information, as it doesn't direct
        pass

    @abstractmethod
    def get_imsavepath(self, vehicle: json_obj, image: bytes) -> str: ...
