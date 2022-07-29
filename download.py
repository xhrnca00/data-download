import argparse
import os
import sys

from pathlib import Path
from typing import List, Optional

from datadwn import defaults
from datadwn.im_saver import ImSaver
from datadwn.json_parser import JsonResponseParser
from datadwn.logger import get_logger
from datadwn.net_downloader import Downloader, NetLevels
from datadwn.save_directors import LocTypeDirector
from datadwn.util import base_off_cwd, json_list

LAST_ARGS_SAVE_PATH = base_off_cwd(
    f"last_{Path(__file__).stem}_args.txt", __file__)

logger = get_logger()


# intellisense, types, overview of args
class DownloadArgs(argparse.Namespace):
    file_prefix: str
    base_url: str
    save_dir: str
    download_delay: float
    both_directions: bool
    file_extension: str
    verify_ssl: bool
    classes_link: str
    net_level: int
    data_limit: int
    input_file: str
    request: Optional[str]


def parse_arguments():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Download car images from CrossWIM API using tanda/http protocol",
        epilog="All urls must be prefixed with schema (https/http)"
    )
    # save args to not have to write arguments every single time
    parser.add_argument("-S", "--save_args", default=defaults.SAVE_ARGS,
                        action="store_true", help="Whether to save arguments into a file")
    parser.add_argument("-p", "--file_prefix", default="THIS FIELD IS REQUIRED",
                        metavar="PREFIX", required=True, help="Prefix of saved images (unique to location)")
    parser.add_argument("-u", "--base_url", default=defaults.BASE_URL,
                        metavar="URL", help="Base url of the HTTP API (without /api/*)")
    parser.add_argument("-d", "--save_dir", default=defaults.SAVE_DIR,
                        metavar="PATH", help="Directory path to store downloaded images")
    parser.add_argument("-t", "--download_delay", type=float, default=defaults.DOWNLOAD_DELAY, metavar="DELAY",
                        help="Time (in seconds) to wait before next API request (to not overwhelm the server)")
    parser.add_argument("--both_directions", metavar="BOOL", default=defaults.BOTH_DIRECTIONS,
                        type=bool, help="Whether to store images of vehicles coming from both directions")
    parser.add_argument("-e", "--file_extension", default=defaults.FILE_EXTENSION,
                        metavar="EXT", help="File extension of images (= format of images in the API)")
    parser.add_argument("--verify_ssl", action="store_true", default=defaults.VERIFY,
                        help="Verify SSL certificates when connecting to the API " +
                        "(self signed certificates give an error)")
    parser.add_argument("--classes_link", metavar="URL",
                        help="If defined, gets the response and checks if it is the same as" +
                        "<url>/api/1.0/classes/list, that was used in testing")

    # partial help message generation from levels
    net_level_texts: List[str] = []
    for level in NetLevels.ALL_LEVELS:
        net_level_texts.append(
            f"{level.number} - {level.name} {level.description}")

    parser.add_argument("-n", "--net_level", type=int, default=defaults.NET_LEVEL, metavar="LEVEL",
                        help="Networks levels to use when reduced network usage is desired, levels: " +
                        f"{', '.join(net_level_texts)}")
    parser.add_argument("-l", "--data_limit", type=int, default=defaults.DATA_LIMIT,
                        metavar="LIMIT", help="Used only for net level 2; limit (in mb) of downloaded data")
    # * add arguments here

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("-i", "--input_file", metavar="PATH", default=defaults.INPUT_FILE,
                             help="Path to already downloaded input json")
    input_group.add_argument("-r", "--request", metavar="LINK",
                             help="Custom request to download the api response")

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


def main():
    args: DownloadArgs = parse_arguments()
    logger.info(args)

    # * info counters
    parsed_vehicles = 0
    downloaded_images = 0
    saved_images = 0

    # * worker objects
    downloader = Downloader(args.base_url, args.download_delay,
                            NetLevels.ALL_LEVELS[args.net_level], args.data_limit, args.verify_ssl)

    remote_classes = None
    if args.classes_link is not None:
        res = downloader.get(args.classes_link, args.net_level == 0)
        if res.ok:
            remote_classes = res.content
            del res
        else:
            logger.critical(
                f"Bad response to json GET: {res.status_code} ({res.reason})")
    parser = JsonResponseParser(remote_classes)
    saver = ImSaver(args.save_dir)
    # only one director at the moment (no argument parsing)
    director = LocTypeDirector(
        parser, args.file_extension, args.file_prefix, "")
    # filtering in the future (possibly)
    # ? another thread/async?
    # ? filer afterwards?

    vehicles: json_list = []
    if args.request is not None:
        res = downloader.get(args.request, args.net_level == 0)
        if res.ok:
            vehicles = parser.str_get_vehicles(res.text)
            del res
        else:
            logger.critical(
                f"Bad response to json GET: {res.status_code} ({res.reason})")
    else:
        vehicles = parser.file_get_vehicles(args.input_file)
    for vehicle in vehicles:
        parsed_vehicles += 1
        # * get images list
        images_list = parser.get_images(vehicle)
        # * get image link
        try:
            image_url = parser.get_prefered_view_link(images_list)
        except ValueError as e:
            logger.error(f"Error while parsing url: {e}")
            continue
        # * download image
        try:
            image = downloader.get_image(image_url)
        except (ConnectionError, WindowsError) as e:
            logger.error(f"Failed to download image: {e}")
            # error is displayed from downloader, as it has more information on the response
            continue
        downloaded_images += 1
        # * save image
        try:
            saver.save_image(image, director.get_imsavepath(vehicle, image))
        except OSError as e:
            logger.error(f"Failed to save image: {e}")
            continue
        saved_images += 1
    logger.success(f"Finished!")
    logger.info(f"Parsed {parsed_vehicles} vehicles")
    logger.info(f"Downloaded {downloaded_images} images")
    logger.success(f"Saved {saved_images} images")


def test():
    parser = CsvResponseParser(None)
    df = parser.get_vehicles(base_off_cwd("./json_ref/export.csv", __file__))
    print(df.ucid)


if __name__ == "__main__":
    main()
