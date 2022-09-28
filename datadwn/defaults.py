import logging as _logging

from os.path import sep as _sep


# Initialize log_level first, as im_downloader uses it
# * preventing a circular import
LOG_LEVEL = _logging.DEBUG

if True:  # NOSONAR
    from .net_worker import NetLevels as _NetLevels
    from .util import base_off_cwd as _base_off_cwd

# download.py args
SAVE_ARGS = False
SAVE_DIR = _base_off_cwd(f"..{_sep}images", __file__)
BASE_URL = "https://localhost"
DOWNLOAD_DELAY = 0.5
FILE_EXTENSION = "jpg"
VERIFY = False
NET_LEVEL = _NetLevels.ZERO.number  # 0
DATA_LIMIT = 10  # in mb
INPUT_FILE = _base_off_cwd(f"..{_sep}vehicles.csv", __file__)
LINK_VERSION = True

# image tags
TAG_PREFERENCE = ("SNAP", "SNAPB")
