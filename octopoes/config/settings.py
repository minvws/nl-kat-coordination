import os
from enum import Enum
from pathlib import Path

from pydantic import BaseSettings


class XTDBType(Enum):
    CRUX = "crux"
    XTDB = "xtdb"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    log_cfg: str = os.path.join(Path(__file__).parent.parent.parent, "logging.yml")
    queue_name_octopoes: str = "octopoes"

    # External services settings
    queue_uri: str = "amqp://guest:guest@rabbitmq:5672/%2fkat"
    xtdb_uri: str = "http://crux:3000"
    xtdb_type: XTDBType = XTDBType.CRUX
