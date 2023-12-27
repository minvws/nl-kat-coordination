import dataclasses
import logging
from typing import Dict, List

from django.core.serializers.json import DjangoJSONEncoder

from octopoes.models import OOI

logger = logging.getLogger(__name__)


def debug_json_keys(data: Dict, path: List) -> None:
    for key, value in data.items():
        if not isinstance(key, (str, int)):
            logger.error("Key %s is type %s, path is %s", key, type(key), path)
        if isinstance(value, dict):
            debug_json_keys(value, path + [key])


class JSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, OOI):
            return str(o)
        elif dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        else:
            return super().default(o)
