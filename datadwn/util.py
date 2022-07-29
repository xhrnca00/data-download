import os as _os

from pathlib import Path as _Path
from typing import Any as _Any
from typing import Dict as _Dict
from typing import List as _List
from typing import Union as _Union

# type aliases
json_obj = _Dict[str, _Any]
json_list = _List[json_obj]
vehicle_type = str
"possible values: car, van, bus, motorbike, truck, lighttruck, industrial"


def round_to_digits(num: float, digits: int) -> _Union[int, float]:
    """
    Rounds a number to specified digits. Returns int if digits <= 0
    """
    return round(num, digits) if digits > 0 else round(num)


def get_relpath(_from: str, to: str) -> str:
    """
    Get a relative path from somewhere to somewhere (inputs can be relative or absolute paths).
    """
    __from = _Path(_from)
    __from = __from.parent if __from.is_file() else __from
    return _os.path.relpath(to, __from)


def base_off_cwd(path: str, _from: str) -> str:
    """
    Returns path relative from current working directory.
    Useful if a path in a file is relative to a file, the file can be ran from anywhere \
        (you can't know the cwd ahead of time).
    If _from is a folder, the string MUST end with a slash!
    """
    return get_relpath(".", _os.path.join(_os.path.dirname(_from), path))
