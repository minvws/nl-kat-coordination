from enum import Enum
from pathlib import Path
from typing import Set

from pydantic import BaseSettings


class XTDBType(Enum):
    CRUX = "crux"
    XTDB = "xtdb"
    XTDB_MULTINODE = "xtdb-multinode"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    log_cfg: str = str(Path(__file__).parent.parent.parent / "logging.yml")  # todo: use Path type
    queue_name_octopoes: str = "octopoes"

    # External services settings
    queue_uri: str = "amqp://guest:guest@rabbitmq:5672/%2fkat"
    xtdb_uri: str = "http://crux:3000"
    xtdb_type: XTDBType = XTDBType.CRUX
    span_export_grpc_endpoint: str = None

    katalogus_api: str = "http://localhost:8003"

    scan_level_recalculation_interval: int = 60
    bits_enabled: Set[str] = set()
    bits_disabled: Set[str] = set()
