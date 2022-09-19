from io import StringIO
from json import loads
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

from .logger import get_logger
from .util import base_off_cwd, json_list, json_obj, t_row, table


logger = get_logger()


_col_types: Dict[str, type] = {
    "vehicleId": np.int32,
    "frontLpCountry": np.str_,
    "frontLpNumber": np.str_,
    "rearLpCountry": np.str_,
    "rearLpNumber": np.str_,
    "timestamp": np.str_,
    "lane": np.str_,
    "gvw": np.int16,
    "length": np.int16,
    "ucid": np.int16,
    "flags.1": np.str_,
    "flags.2": np.str_,
    "flags.3": np.str_,
    "flags.4": np.str_,
    "flags.5": np.str_,
    "flags.6": np.str_,
    "flags.7": np.str_,
    "flags.8": np.str_,
    "flags.9": np.str_,
    "flags.10": np.str_,
}


# CSV
class CsvResponseParser:
    def _check_csv_cols(self, remote_head: List[str]) -> None:
        with open(base_off_cwd("./csv_info.json", __file__), "r") as file:
            local_head: List[str] = loads(file.read())["head"]
        local_head = [
            col for col in local_head if not col.startswith("flags")]
        remote_head = [
            col for col in remote_head if not col.startswith("flags")]
        # no assert, because we might want to catch the error
        if local_head != remote_head:
            logger.error(f"Wrong csv head: {remote_head} != {local_head}")
            logger.info("(remote != local)")
            raise ValueError("CSV head is not the same as expected")

    def get_vehicles(self, path_or_buffer: Union[str, StringIO]) -> table:
        veh_df = pd.read_csv(filepath_or_buffer=path_or_buffer, sep=";",
                             dtype=_col_types, usecols=(lambda x: x in _col_types.keys()))
        self._check_csv_cols(list(veh_df.keys()))
        return veh_df

    def get_timestamp(self, vehicle: t_row) -> Optional[str]:
        try:
            return vehicle.timestamp  # type: ignore[attr-defined]
        except AttributeError:
            logger.error("timestamp not in the row")
            logger.debug(f"Row:\n{vehicle}")
            return None

    def get_id(self, vehicle: t_row) -> Optional[int]:
        try:
            return vehicle.vehicleId  # type: ignore[attr-defined]
        except AttributeError:
            logger.error("vehicleId not in the row")
            logger.debug(f"Row:\n{vehicle}")
            return None
# ENHANCE: add more getters (LPs)


# vehicle/detail JSON
class JsonResponseParser:
    def get_vehicle(self, contents: str) -> json_obj:
        "raises value error, if no vehicle"
        try:
            return loads(contents)["data"]
        except KeyError:
            logger.debug(f"Object: {contents}")
            raise ValueError("Vehicle object not in json")

    def get_images(self, vehicle: json_obj) -> json_list:
        try:
            return vehicle["images"]
        except KeyError:
            logger.warning("images not in the object")
            logger.debug(f"Object: {vehicle}")
            return []

    def get_timestamp(self, vehicle: json_obj) -> Optional[str]:
        try:
            return vehicle["timestamp"]
        except KeyError:
            logger.warning("timestamp not in the object")
            logger.debug(f"Object: {vehicle}")
            return None

    def get_ucid(self, vehicle: json_obj) -> Optional[int]:
        try:
            return vehicle["ucid"]
        except KeyError:
            logger.warning("ucid not in the object")
            logger.debug(f"Object: {vehicle}")
            return None

    def get_lane(self, vehicle: json_obj) -> Optional[str]:
        try:
            return vehicle["lane"]
        except KeyError:
            logger.warning("lane not in the object")
            logger.debug(f"Object: {vehicle}")
            return None

    def get_lane_description(self, vehicle: json_obj) -> Optional[str]:
        try:
            return vehicle["laneDescription"]
        except KeyError:
            logger.warning("laneDescription not in the object")
            logger.debug(f"Object: {vehicle}")
            return None
