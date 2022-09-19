import argparse
import asyncio
import os
import random
import time

from hashlib import md5
from string import ascii_lowercase
from typing import Dict, Optional

from httpx import ConnectError

from .defaults import TAG_PREFERENCE
from .im_saver import ImSaver
from .logger import get_logger
from .net_worker import NetLevels, NetWorker
from .parser import CsvResponseParser, JsonResponseParser
from .util import json_list, json_obj, t_row, veh_type


logger = get_logger()


# intellisense, types, overview of args
class DownloaderArgs(argparse.Namespace):
    loc_code: Optional[str]
    base_url: str
    save_dir: str
    download_delay: float
    file_extension: str
    verify_ssl: bool
    input_file: str
    net_level: int
    data_limit: int
    link_has_number: bool


class Downloader:
    def __init__(self, args: DownloaderArgs):
        logger.warning(
            "Classes ucids may be different than seen " +
            "(all machines have their class/list json a little different)")
        # * info counters
        self.parsed_vehicles = 0
        self.downloaded_images = 0
        self.saved_images = 0

        # * worker objects
        self.csv_parser = CsvResponseParser()
        self.vehicles = self.csv_parser.get_vehicles(args.input_file)
        self.net_worker = NetWorker(
            args.base_url,
            NetLevels.ALL_LEVELS[args.net_level],
            args.download_delay,
            args.data_limit,
            args.verify_ssl,
        )
        self.json_parser = JsonResponseParser()
        if args.loc_code is None:
            args.loc_code = "".join(random.choice(ascii_lowercase)
                                    for _ in range(2))
            logger.info(f"Random file prefix: {args.loc_code}")
        self.director = LocTypeDirector(self.json_parser, args.file_extension,
                                        args.loc_code)
        self.saver = ImSaver(args.save_dir)
        self.link_has_version = args.link_has_number

    async def get_images(self) -> None:
        start = time.perf_counter()
        try:
            await asyncio.gather(*(
                self.get_image(vehicle) for vehicle  # type: ignore[arg-type]
                in self.vehicles.itertuples(name="Vehicle")
            ))
        finally:
            # we have to close the connection
            await self.net_worker.close_connection()
        logger.success("Finished!")
        logger.info(f"Parsed vehicles: {self.parsed_vehicles}")
        logger.info(
            f"Saved {self.saved_images}/{self.downloaded_images} images")
        logger.info(f"Took: {time.perf_counter() - start:.2f}s")

    # ENHANCE: move to functions, use df.apply
    async def get_image(self, veh_row: t_row) -> None:
        # TODO: filter vehicle
        # přestupek -> keep
        # moc disku -> mažou zbytek
        # * get json link
        v_id = self.csv_parser.get_id(veh_row)
        if v_id is None:
            return
        json_link = self._create_json_link(v_id)
        # * download json
        try:
            veh_json = await self._download_json(json_link)
        except (ConnectError, ValueError) as e:  # TODO: handle ValueError in a different place
            logger.error(f"Error downloading json: {e}, " +
                         f"url: {self.net_worker.get_full_url(json_link)}")
            return
        # * get image link
        try:
            image_link = get_preferred_view_link(
                self.json_parser.get_images(veh_json))
        except ValueError as e:
            logger.error(f"Error getting image url: {e}")
            return
        self.parsed_vehicles += 1
        # * download image
        try:
            image = await self._download_image(image_link)
        except ConnectError as e:
            logger.error(f"Error downloading image: {e}, " +
                         f"url: {self.net_worker.get_full_url(image_link)}")
            return
        self.downloaded_images += 1
        # TODO: filter image
        # * save image
        image_path = self.director.get_imsavepath(veh_json, image)
        try:
            await self.saver.save_image(image, image_path)
        except OSError as e:
            logger.error(f"Error saving image: {e}")
            return
        self.saved_images += 1

    def _create_json_link(self, id: int) -> str:
        # TODO: does every cam leave API version out of the link in vehicle/detail?
        # ? probably not -> self.link_has_version
        return f"/api{'/1.0' if self.link_has_version else ''}/vehicle/detail?id={id}"

    async def _download_image(self, api_url: str) -> bytes:
        """Raises ConnectError if response is not 2**"""
        res = await self.net_worker.get(api_url)
        if res.is_success:
            return res.content
        else:
            raise ConnectError(
                f"Server responded with a bad status code: {res.status_code} ({res.reason_phrase})")

    async def _download_json(self, api_url: str) -> json_obj:
        """Raises ConnectError if response is not 2**"""
        res = await self.net_worker.get(api_url)
        if res.is_success:
            return self.json_parser.get_vehicle(res.text)
        else:
            raise ConnectError(
                f"Server responded with a bad status code: {res.status_code} ({res.reason_phrase})")


def get_preferred_view_link(images_list: json_list) -> str:
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


def resolve_ucid(ucid: int) -> Optional[veh_type]:
    if ucid in (1, 3, 4):
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
        return f"lighttruck_{ucid}"
    elif ucid in (
        # without image data, there is no real way to differentiate
        6, 9, 10, 11, 13, 18, 19, 20, 21, 22, 23, 24, 25, 26, 29,
        32, 38, 39, 40, 41, 42, 43, 50, 52, 53, 54, 60, 61, 63, 64,
        65, 66, 67, 68, 70, 71, 72, 79, 403, 611, 612, 613, 614, 615,
    ):
        return f"truck_{ucid}"
    else:
        return None


class LocTypeDirector():
    def __init__(self, json_parser: JsonResponseParser, file_extension: str,
                 default_loc_code: str) -> None:
        self.json_parser = json_parser
        self.file_ext = file_extension
        self.loc_code = default_loc_code

    def get_imsavepath(self, vehicle: json_obj, image: bytes) -> str:
        ucid = self.json_parser.get_ucid(vehicle)
        v_type = None if ucid is None else resolve_ucid(ucid)
        type_dir = f"undefined_{ucid}" if v_type is None else v_type
        l_code = self.json_parser.get_lane_description(vehicle)
        if l_code is None:
            l_code = self.loc_code
        else:
            l_code = l_code.rsplit(",", 1)[1].strip()
        lane = self.json_parser.get_lane(vehicle)
        if lane is not None:
            l_code += "_" + lane
        # ENHANCE: better time processing
        timestamp = self.json_parser.get_timestamp(vehicle)
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
