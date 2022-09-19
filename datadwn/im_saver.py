import os

from typing import List

import aiofiles
import aiofiles.os
import aiofiles.ospath

from .logger import get_logger


logger = get_logger()


class ImSaver:
    def __init__(self, save_dir: str) -> None:
        self.save_dir = save_dir
        self.dir_exist_cache: List[str] = []

    async def ensure_folders_exist(self, path: str) -> None:
        """last path element must be a directory as well"""
        if path not in self.dir_exist_cache:
            await aiofiles.os.makedirs(path, mode=1, exist_ok=True)
            self.dir_exist_cache.append(path)

    async def save_image(self, imdata: bytes, filepath: str) -> None:
        """
        filepath is relative to save_dir (save_dir being / (=root))
        throws OSError if file already exists
        """
        image_path = os.path.join(self.save_dir, filepath)
        await self.ensure_folders_exist(os.path.dirname(image_path))
        if await aiofiles.ospath.exists(image_path):
            raise OSError(f"File {image_path} already exists")
        async with aiofiles.open(image_path, "wb") as imfile:
            await imfile.write(imdata)
            logger.debug(f"Saved image to {image_path}")
