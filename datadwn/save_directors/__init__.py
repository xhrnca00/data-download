from typing import Dict as _Dict
from typing import Type as _Type

from .base_director import BaseDirector as _BaseDirector
from .loc_type_director import LocTypeDirector

all_directors_dict: _Dict[str, _Type[_BaseDirector]] = {
    "LocType": LocTypeDirector
}
