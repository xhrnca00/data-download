import asyncio

from dataclasses import dataclass
from time import time
from typing import Any, Coroutine

import httpx

from aioconsole import ainput

from .logger import get_logger
from .util import round_to_digits


logger = get_logger()


MAX_REQUEST_LIMIT = 10


# net levels (for bandwith and data saving)
@dataclass(frozen=True)
class NetworkLevel:
    number: int
    name: str
    description: str


class NetLevels():
    ZERO = NetworkLevel(0, "[CONFIRM_DOWNLOAD]",
                        "Ask for permission before every download")
    ONE = NetworkLevel(1, "[DOWNLOAD_LIMIT]",
                       "Have a limited download size")
    TWO = NetworkLevel(2, "[DOWNLOAD_DELAY]",
                       "Have a delay between downloads to not overwhelm the API client")
    THREE = NetworkLevel(3, "[FAST_DOWNLOAD]",
                         "GET all links at the \"same time\" using async")
    ALL_LEVELS = (ZERO, ONE, TWO, THREE)

    def __new__(cls):
        logger.critical(f"{cls.__name__} class is instanceless")
        raise PermissionError("Could not instantiate")


class NetWorker:
    def __init__(self, base_url: str, net_level: NetworkLevel,
                 download_delay: float, data_limit: int, verify: bool) -> None:
        # * check if initialized in async runtime (locks need to be created within a loop)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            logger.critical(f"{type(self).__name__} __init__ method " +
                            "not running in an async loop (needed for Lock initialization)")
            exit(1)  # not-ok status code
        # * proceed with initialization like normal
        self.base_url = base_url
        self.verify = verify
        self.__init_client()
        self.level = net_level
        self.__init_net_level(download_delay, data_limit)
        self.flying_requests = 0
        self._flying_lock = asyncio.Lock()
        logger.debug(
            f"Initialized {type(self).__name__} with NetLevel {net_level.number}")

    def __init_client(self) -> None:
        self.client = httpx.AsyncClient(follow_redirects=True,
                                        base_url=self.base_url, verify=self.verify)

    def __init_net_level(self, download_delay: float, data_limit: int):
        if self.level == NetLevels.ZERO:
            self._get_func = self._get_level_0
        elif self.level == NetLevels.ONE:
            self.data_limit = data_limit
            self.used_data = 0
            self._count_lock = asyncio.Lock()
            self._get_func = self._get_level_1
        elif self.level == NetLevels.TWO:
            self._get_func = self._get_level_2
        elif self.level == NetLevels.THREE:
            self._get_func = self._get_level_3
        else:
            logger.warning("No known net level specified, setting to 0")
            self._get_func = self._get_level_0

        # * level < 3 vars
        if self.level != NetLevels.THREE:
            # delay is present in all others
            self.delay = download_delay
            self.last_request = time() - self.delay
            self._get_lock = asyncio.Lock()
            # * level < 2 vars
        if self.level in (NetLevels.ZERO, NetLevels.ONE):
            # asking is present in 0 and 1
            self._ask_lock = asyncio.Lock()
            logger.important(
                "Because of async code, the logger might \"write\" into the input fields. " +
                "This does not affect the response though, so a classic y/n + enter is enough. " +
                "This can't really be fixed, sorry for the inconveniece!"
            )

    async def close_connection(self) -> None:
        await self.client.aclose()
        logger.debug("Closed client connection")

    def __del__(self):
        if not self.client.is_closed:
            logger.critical(
                "Client connections not closed (potential resource leak)!" +
                f" hint: call {type(self).__name__}.close_connection()" +
                " (calling in a try-finally block recommended)")
            logger.info("Trying anyway")
            # * create new event loop for finishing cleanup
            asyncio.new_event_loop().run_until_complete(self.close_connection())

    def get_full_url(self, api_url: str) -> str:
        """Create full url from api url (starting with /)"""
        return self.base_url + api_url

    def get(self, api_url: str, bypass=False) -> Coroutine[Any, Any, httpx.Response]:
        """
        GET an api url asyncronously.

        If bypass is False, use get according to NetLevel
        If it is True and level is 3, GET without no delay
        Else GET, but using download_delay

        *Might throw ConnectError* (or other unseen one)
        """
        if not bypass:
            f = self._get_func
        elif self.level == NetLevels.THREE:
            f = self._get_level_3
        else:
            f = self._get_level_2
        return f(api_url)

    def _not_sent_response(self, api_url: str) -> httpx.Response:
        return httpx.Response(412, request=httpx.Request(method="GET", url=self.get_full_url(api_url)))

    async def _get_level_0(self, api_url: str) -> httpx.Response:
        async with self._ask_lock:
            # ENHANCE: allow to answer multiple questions at once (10y or 5y5n for instance)
            # ENHANCE: figure out how to use ainput without logs flooding the input field
            i_res = (await ainput(f"Download {self.get_full_url(api_url)}? (Y/n): ")).lower()
        if i_res == "y":
            return await self._get_level_2(api_url)
        else:
            logger.info(f"Not getting {self.get_full_url(api_url)}")
            return self._not_sent_response(api_url)

    async def _get_level_1(self, api_url: str) -> httpx.Response:
        async with self._count_lock:
            if self.used_data > self.data_limit:
                logger.warning(
                    f"Downloads over the limit! ({self.used_data}/{self.data_limit} bytes)")
                res = await self._get_level_0(api_url)
            else:
                res = await self._get_level_2(api_url)
            self.used_data += len(res.content)
            logger.info(
                f"Used data so far: {self.used_data}/{self.data_limit} bytes")
        return res

    async def _get_level_2(self, api_url: str) -> httpx.Response:
        async with self._get_lock:
            sleep_dur = self.last_request + self.delay - time()
            if sleep_dur > 0:
                logger.info(f"sleeping for {round_to_digits(sleep_dur, 3)} s")
                await asyncio.sleep(sleep_dur)
            r = await self._get_level_3(api_url)
            self.last_request = time()
        return r

    async def _get_level_3(self, api_url: str) -> httpx.Response:
        if self.flying_requests >= (MAX_REQUEST_LIMIT - 1):
            logger.info("Waiting for requests to finish")
            logger.debug(f"Currrently flying requests: {self.flying_requests}")
            await self._flying_lock.acquire()
        self.flying_requests += 1
        try:
            res = await self._actual_get(api_url)
            return res
        finally:
            if self.flying_requests == MAX_REQUEST_LIMIT:
                self._flying_lock.release()
            self.flying_requests -= 1

    async def _actual_get(self, api_url: str) -> httpx.Response:
        logger.important(f"GET: {self.get_full_url(api_url)}")
        try:
            return await self.client.get(api_url)
        except RuntimeError as e:
            if self.client.is_closed:
                logger.warning("Client already closed")
                logger.info("Creating a new client")
                self.__init_client()
                return await self.client.get(api_url)
            else:
                raise e
