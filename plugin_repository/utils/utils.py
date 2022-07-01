import logging
from pathlib import Path
from typing import Union, Dict

import yaml
from pydantic import parse_obj_as

from plugin_repository.models import Plugin, PluginType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config_file(path: Union[str, Path]) -> Plugin:
    path = Path(path)

    with path.open() as file:
        return parse_config(yaml.full_load(file))


def parse_config(obj: Dict) -> Plugin:
    return parse_obj_as(PluginType, obj)
