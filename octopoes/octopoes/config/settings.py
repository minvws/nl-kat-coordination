from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional, Set

from pydantic import BaseSettings

from octopoes.models import ScanLevel, ScanProfileType
from octopoes.models.ooi.findings import RiskLevelSeverity


class XTDBType(Enum):
    XTDB_MULTINODE = "xtdb-multinode"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    log_cfg: str = str(
        Path(__file__).parent.parent.parent / "logging.yml"
    )  # Follow-up ticket to make logging the same for all modules?

    # External services settings
    queue_uri: str = "amqp://guest:guest@rabbitmq:5672/%2fkat"
    xtdb_uri: str = "http://crux:3000"
    xtdb_type: XTDBType = XTDBType.XTDB_MULTINODE  # TODO remove all legacy CRUX/XTDB support
    span_export_grpc_endpoint: Optional[str] = None

    katalogus_api: str = "http://localhost:8003"

    scan_level_recalculation_interval: int = 60
    bits_enabled: Set[str] = set()
    bits_disabled: Set[str] = set()


DEFAULT_SCAN_LEVEL_FILTER = {scan_level for scan_level in ScanLevel}
DEFAULT_SCAN_PROFILE_TYPE_FILTER = {scan_profile_type for scan_profile_type in ScanProfileType}
DEFAULT_SEVERITY_FILTER = {severity for severity in RiskLevelSeverity}
DEFAULT_LIMIT = 50
DEFAULT_OFFSET = 0
QUEUE_NAME_OCTOPOES: str = "octopoes"
