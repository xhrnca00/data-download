from hashlib import md5
from json import JSONDecodeError, loads
from typing import Dict, Generator, Optional

from .defaults import TAG_PREFERENCE
from .logger import get_logger
from .util import base_off_cwd, json_list, json_obj, vehicle_type

logger = get_logger()


# TODO: parse csv instead (lol)
class JsonResponseParser:
    def __init__(self, remote_classes: Optional[bytes]) -> None:
        """verifies remote_classes if it is not None"""
        logger.warning("File parser using utf-8 encoding")
        logger.warning("might not be the encoding used in the actual file")
        logger.warning("(It was in testing)")
        self.use_class_list = True
        # * verify class list
        if remote_classes is not None:
            with open(base_off_cwd("./classes_info.json", __file__)) as file:
                content = loads(file.read())
            # same hash
            same_hash = content["md5hash"] == md5(remote_classes).hexdigest()
            # same len
            try:
                remote_object = loads(remote_classes.decode(encoding="utf-8"))
            except JSONDecodeError as e:
                logger.warning("Failed to decode json")
                logger.debug(
                    f"default encoding decode: {remote_classes.decode()}, error: {e}")
            try:
                remote_len = len(remote_object["data"]["classes"])
            except KeyError:
                logger.warning("Classes list not in the object")
                logger.debug(f"Object: {remote_object}")
            same_len = remote_len == content["len"]
            proceed: str
            if not same_hash or not same_len:
                logger.warning("Class list might not be the same")
                logger.warning(
                    f"Same hash? {same_hash}\nSame length? {same_len}")
                proceed = input(
                    "Do you want to use known class list uids anway? (Y/n)").lower()
                if proceed != "y":
                    self.use_class_list = False

    def str_get_vehicles(self, contents: str) -> json_list:
        try:
            return loads(contents)["data"]["vehicles"]
        except KeyError:
            logger.error("vehicles is not in the json")
            logger.debug(f"Object: {contents}")
            return []

    def file_get_vehicles(self, path: str) -> json_list:
        with open(path, encoding="utf-8") as file:
            return self.str_get_vehicles(file.read())

    def get_images(self, vehicle: json_obj) -> json_list:
        """might throw a Key Error (up to the user)"""
        try:
            return vehicle["images"]
        except KeyError:
            logger.warning("images not in the object")
            logger.debug(f"Object: {vehicle}")
            return []

    def get_images_all(self, veh_list: json_list) -> Generator[json_list, None, None]:
        for vehicle in veh_list:
            yield self.get_images(vehicle)

    def get_timestamp(self, vehicle: json_obj) -> Optional[str]:
        try:
            return vehicle["timestamp"]
        except KeyError:
            logger.warning("timestamp not in the object")
            logger.debug(f"Object: {vehicle}")
            return None

    def get_vehicle_type(self, vehicle: json_obj) -> Optional[vehicle_type]:
        try:
            return self.resolve_ucid(vehicle["ucid"])
        except KeyError:
            logger.warning("ucid not in the object")
            logger.debug(f"Object: {vehicle}")
            return None

    def resolve_ucid(self, ucid: int) -> Optional[vehicle_type]:
        if not self.use_class_list:
            return None
        if ucid in (1, 3,):
            return f"car_{ucid}"
        elif ucid in (2, 31, 34, 35, 51, 55, 56,):
            return f"van_{ucid}"
        elif ucid in (27, 28, 36, 44, 57,):
            return f"bus_{ucid}"
        elif ucid in (30,):
            return f"motorbike_{ucid}"
        elif ucid in ():
            # * there is no class for industrial, as their axles could be anything
            logger.critical(f"There is no way you got here, ucid: {ucid}")
            return f"industrial_{ucid}"
        elif ucid in (5,):
            logger.critical(
                f"lighttruck classification is TODO, you should not be here, ucid: {ucid}")
            return f"lighttruck_{ucid}"
        elif ucid in (
            # there are lighttrucks in this
            # without image data, there is no way to differentiate
            6, 9, 10, 11, 13, 18, 19, 20, 21, 22, 23, 24, 25, 26, 29,
            32, 38, 39, 40, 41, 42, 43, 50, 52, 53, 54, 60, 61, 63, 64,
            65, 66, 67, 68, 70, 71, 72, 79, 403, 611, 612, 613, 614, 615,
        ):
            return f"truck_{ucid}"
        else:
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

    def get_prefered_view_link(self, images_list: json_list) -> str:
        """raises ValueEror if something is wrong"""
        if len(images_list) == 0:
            raise ValueError("No images in the object")
        images_dict: Dict[str, str] = {}
        for image_obj in images_list:
            images_dict[image_obj["tag"]] = image_obj["url"]
        for key in TAG_PREFERENCE:
            if key in images_dict.keys():
                return images_dict[key]
            else:
                logger.info(f"key [{key}] not in images")
        raise ValueError(f"No known tags in image list: {images_list}, " +
                         f"known usable tags: {TAG_PREFERENCE}")
