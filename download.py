import argparse
import asyncio
import os
import sys

from pathlib import Path
from typing import List

from datadwn import defaults
from datadwn.logger import get_logger
from datadwn.logic import Downloader, DownloaderArgs
from datadwn.net_worker import NetLevels
from datadwn.util import base_off_cwd


logger = get_logger()


def parse_arguments():
    # ENHANCE: required flag "--verified_classes" | "-v", implying, that the caller has checked remote class/list
    LAST_ARGS_SAVE_PATH = base_off_cwd(
        f"last_{Path(__file__).stem}_args.txt", __file__)

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Download car images from CrossWIM API using tanda/http protocol",
        epilog="All urls must be prefixed with schema (https/http)"
    )
    # save args to not have to write arguments every single time
    parser.add_argument("-S", "--save_args", default=defaults.SAVE_ARGS,
                        action="store_true", help="Whether to save arguments into a file")
    parser.add_argument("-c", "--loc_code", "--default_code", default=None, metavar="CODE",
                        help="Default prefix of saved images (unique to location),\
                            used if lane descritpion is not present; random if left None")
    parser.add_argument("-u", "--base_url", default=defaults.BASE_URL,
                        metavar="URL", help="Base url of the HTTP API (without /api/*)")
    parser.add_argument("-o", "--save_dir", default=defaults.SAVE_DIR,
                        metavar="PATH", help="Directory path to store downloaded images")
    parser.add_argument("-t", "--download_delay", type=float, default=defaults.DOWNLOAD_DELAY, metavar="DELAY",
                        help="Time (in seconds) to wait before next API request (to not overwhelm the server)")
    parser.add_argument("--file_extension", default=defaults.FILE_EXTENSION,
                        metavar="EXT", help="File extension of images (= format of images in the API)")
    parser.add_argument("--verify_ssl", action="store_true", default=defaults.VERIFY,
                        help="Verify SSL certificates when connecting to the API " +
                        "(self signed certificates give an error)")
    parser.add_argument("-i", "--input_file", default=defaults.INPUT_FILE,
                        metavar="PATH", help="Path to already downloaded input csv")

    # partial help message generation from levels
    net_level_texts: List[str] = []
    for level in NetLevels.ALL_LEVELS:
        net_level_texts.append(
            f"{level.number} - {level.name} {level.description}")

    parser.add_argument("-n", "--net_level", type=int, default=defaults.NET_LEVEL, metavar="LEVEL",
                        help="Network levels to use when reduced network usage is desired, levels: " +
                        f"{', '.join(net_level_texts)}")
    parser.add_argument("--data_limit", "--download_limit", type=float, default=defaults.DATA_LIMIT,
                        metavar="LIMIT", help="Used only for net level 2; limit (in mb) of downloaded data")
    parser.add_argument("-l", "--link_has_number", default=defaults.LINK_VERSION, required=True,
                        type=bool, help="Whether the links to vehicle/detail have api version number in them; this field is required")
    # * add arguments here

    if len(sys.argv) == 1 and os.path.exists(LAST_ARGS_SAVE_PATH):
        with open(LAST_ARGS_SAVE_PATH) as file:
            args = parser.parse_args(file.read().split())
    else:
        args = parser.parse_args()
        if args.save_args:
            with open(LAST_ARGS_SAVE_PATH, "w") as file:
                file.write(" ".join(sys.argv[1:]))
    # from megabytes to bytes
    args.data_limit *= 1_048_576
    return args


async def main():
    args: DownloaderArgs = parse_arguments()
    logger.info(args)

    downloader = Downloader(args)
    await downloader.get_images()


if __name__ == "__main__":
    asyncio.run(main())
