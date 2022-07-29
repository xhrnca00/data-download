import os
import random

from hashlib import md5
from string import ascii_lowercase

from ..json_parser import JsonResponseParser
from ..util import json_obj
from .base_director import BaseDirector


class LocTypeDirector(BaseDirector):
    def __init__(self, json_parser: JsonResponseParser, file_extension: str,
                 loc_code: str, device_name: str) -> None:
        self.parser = json_parser
        self.file_ext = file_extension
        self.loc_code = loc_code
        self.d_hash = md5(device_name.encode()).hexdigest()[:2]

    def get_imsavepath(self, vehicle: json_obj, image: bytes) -> str:
        v_type = self.parser.get_vehicle_type(vehicle)
        type_dir: str = "undefined" if v_type is None else v_type
        l_code = self.parser.get_lane_description(vehicle)
        if l_code is None:
            l_code = self.loc_code
        else:
            l_code = l_code.rsplit(",", 1)[1].strip()
        lane = self.parser.get_lane(vehicle)
        if lane is not None:
            l_code += "_" + lane
        l_code += "-" + self.d_hash
        # ENHANCE: better time processing
        timestamp = self.parser.get_timestamp(vehicle)
        if timestamp is None:
            timestamp = md5(image).hexdigest()[:6] +\
                "".join(random.choice(ascii_lowercase) for _ in range(6))
        else:
            timestamp = timestamp\
                .replace(":", "")\
                .replace("-", "")\
                .rsplit("+", 1)[0][:-3]
        final_path = os.path.join(l_code, type_dir,
                                  f"{l_code}#{timestamp}.{self.file_ext}")
        return final_path
