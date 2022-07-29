
from dataclasses import dataclass
from time import sleep, time
from typing import Callable, Generator, Iterable

import requests

from urllib3 import disable_warnings

from .logger import get_logger
from .util import base_off_cwd, round_to_digits

disable_warnings()
logger = get_logger()


# net levels (for bandwith and data saving)
@dataclass(frozen=True)
class NetworkLevel:
    number: int
    name: str
    description: str


class NetLevels():
    ZERO = NetworkLevel(0, "[MOCK_DOWNLOAD]",
                        "Log instead of downloading (useful for debugging)")
    ONE = NetworkLevel(1, "[CONFIRM_DOWNLOAD]",
                       "Ask for permission before every download")
    TWO = NetworkLevel(2, "[DOWNLOAD_LIMIT]",
                       "Have a limited download size")
    THREE = NetworkLevel(3, "[DOWNLOAD_DELAY]",
                         "Have a delay between downloads to not overwhelm the API client")
    ALL_LEVELS = (ZERO, ONE, TWO, THREE)

    def __new__(cls):
        logger.critical(f"{cls.__name__} class is instanceless")
        raise PermissionError("Could not instantiate")


class Downloader:
    def __init__(self, base_url: str, download_delay: float,
                 net_level: NetworkLevel, data_limit: int, verify: bool) -> None:
        self.base_url = base_url
        self.delay = download_delay
        self.verify = verify
        self.level = net_level
        self.last_download = time() - self.delay

        self._get_func: Callable[[str], requests.Response]
        if net_level == NetLevels.ZERO:
            self._get_func = self._get_level_0
        elif net_level == NetLevels.ONE:
            self._get_func = self._get_level_1
        elif net_level == NetLevels.TWO:
            self._init_level_2_vars(data_limit)
            self._get_func = self._get_level_2
        elif net_level == NetLevels.THREE:
            self._get_func = self._get_level_3
        else:
            logger.warning("No known net level specified, setting to 0")
            self._get_func = self._get_level_0
        logger.debug(
            f"Initialized {type(self).__name__} with NetLevel {net_level.number}")

    def get(self, url: str, bypass: bool) -> requests.Response:
        return self._actual_get(url) if bypass else self._get_func(url)

    def ensure_delay(self) -> None:
        sleep_dur = self.last_download + self.delay - time()
        if sleep_dur > 0:
            logger.info(f"sleeping for {round_to_digits(sleep_dur, 3)} s")
            sleep(sleep_dur)
        self.last_download = time()

    def get_image(self, api_url: str) -> bytes:
        """Raises ConnectionError if response is not ok"""
        full_url = self.base_url + api_url
        res = self._get_func(full_url)
        if res.ok:
            return res.content
        else:
            raise ConnectionError(
                f"Server responded with a bad status code: {res.status_code} ({res.reason}), url: {res.url}")

    def get_images(self, url_iter: Iterable[str]) -> Generator[bytes, None, None]:
        for url in url_iter:
            image = self.get_image(url)
            if image is not None:
                yield image

    # level 2 requires tracking of network data usage
    def _init_level_2_vars(self, data_limit: int) -> None:
        self.data_limit = data_limit
        self.used_data = 0

    def _not_sent_response(self, url: str) -> requests.Response:
        res = requests.Response()
        res.url = url
        if self.level == NetLevels.ZERO:
            res.status_code = 204  # No Content
            with open(base_off_cwd("./mock_image.jpg", __file__), "rb") as image:
                res._content = image.read()
        else:
            res.status_code = 406  # Not Acceptable
            res.reason = "Request was not sent"
        return res

    def _get_level_0(self, url: str) -> requests.Response:
        logger.info(f"GET: {url}")
        return self._not_sent_response(url)

    def _get_level_1(self, url: str) -> requests.Response:
        i_res = input(f"Download {url}? (Y/n): ").lower()
        if i_res == "y":
            return self._actual_get(url)
        else:
            logger.info(f"Not getting {url}")
            return self._not_sent_response(url)

    def _get_level_2(self, url: str) -> requests.Response:
        if self.used_data > self.data_limit:
            logger.warning(
                f"Downloads over the limit! ({self.used_data}/{self.data_limit})")
            res = self._get_level_1(url)
        else:
            res = self._actual_get(url)
        if res.ok:
            self.used_data += len(res.content)
            logger.info(f"Used data so far: {self.used_data}")
        return res

    def _get_level_3(self, url: str) -> requests.Response:
        return self._actual_get(url)

    def _actual_get(self, url: str) -> requests.Response:
        logger.info(f"GET: {url}")
        self.ensure_delay()
        return requests.get(url, stream=True, verify=self.verify)
