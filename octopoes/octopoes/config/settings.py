from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional, Set

from pydantic import AmqpDsn, AnyHttpUrl, BaseSettings, Field

from octopoes.models import ScanLevel, ScanProfileType
from octopoes.models.ooi.findings import RiskLevelSeverity


class XTDBType(Enum):
    CRUX = "crux"
    XTDB = "xtdb"
    XTDB_MULTINODE = "xtdb-multinode"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    log_cfg: str = str(Path(__file__).parent.parent.parent / "logging.yml")

    # External services settings
    queue_uri: AmqpDsn = Field("amqp://", description="KAT queue URI", env="QUEUE_URI")
    xtdb_uri: str = Field("http://crux:3000", description="XTDB API", env="XTDB_URI")
    xtdb_type: XTDBType = XTDBType.XTDB_MULTINODE

    span_export_grpc_endpoint: Optional[str] = Field(None, env="SPAN_EXPORT_GRPC_ENDPOINT")

    katalogus_api: AnyHttpUrl = Field("http://localhost:8003", description="Katalogus API URL", env="KATALOGUS_API")

    scan_level_recalculation_interval: int = Field(60, description="Scan level recalculation interval in seconds")
    bits_enabled: Set[str] = Field(set(), description="Explicitly enabled bits")
    bits_disabled: Set[str] = Field(set(), description="Explicitly disabled bits")

    class Config:
        env_prefix = "OCTOPOES_"


DEFAULT_SCAN_LEVEL_FILTER = {scan_level for scan_level in ScanLevel}
DEFAULT_SCAN_PROFILE_TYPE_FILTER = {scan_profile_type for scan_profile_type in ScanProfileType}
DEFAULT_SEVERITY_FILTER = {severity for severity in RiskLevelSeverity}
DEFAULT_LIMIT = 50
DEFAULT_OFFSET = 0
QUEUE_NAME_OCTOPOES: str = "octopoes"
