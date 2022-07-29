import os

from .logger import get_logger

logger = get_logger()


class ImSaver:
    def __init__(self, save_dir: str) -> None:
        self.save_dir = save_dir

    def ensure_folders_exist(self, path: str) -> None:
        """last path element must be a directory as well"""
        # ENHANCE: possibly cache existing directories
        os.makedirs(path, mode=1, exist_ok=True)

    def save_image(self, imdata: bytes, filepath: str) -> None:
        """
        filepath is relative to save_dir (save_dir being / (=root))
        throws OSError if file already exists
        """
        image_path = os.path.join(self.save_dir, filepath)
        self.ensure_folders_exist(os.path.dirname(image_path))
        if os.path.exists(image_path):
            raise OSError(f"File {image_path} already exists")
        with open(image_path, "wb") as imfile:
            imfile.write(imdata)
            logger.debug(f"Saved image to {image_path}")
