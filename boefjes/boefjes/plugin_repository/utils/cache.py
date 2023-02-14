from pathlib import Path
from typing import Dict

import diskcache

_CACHE: Dict[Path, diskcache.Cache] = {}


def get_or_create_cache(location: Path) -> diskcache.Cache:
    if location in _CACHE:
        return _CACHE[location]

    cache = diskcache.Cache(location.as_posix())
    _CACHE[location] = cache

    return cache
