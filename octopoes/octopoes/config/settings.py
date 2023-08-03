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
    log_cfg: str = Field(str(Path(__file__).parent.parent.parent / "logging.yml"))

    # External services settings
    queue_uri: AmqpDsn = Field(..., example="amqp://", description="KAT queue URI", env="QUEUE_URI")
    xtdb_uri: AnyHttpUrl = Field(..., example="http://crux:3000", description="XTDB API", env="XTDB_URI")
    xtdb_type: XTDBType = Field(
        XTDBType.XTDB_MULTINODE,
        description="Determines how Octopoes will format documents' primary in serialization (crux.db/id vs xt/id)",
        possible_values=["crux", "xtdb", "xtdb-multinode"],
    )

    katalogus_api: AnyHttpUrl = Field(
        ..., example="http://localhost:8003", description="Katalogus API URL", env="KATALOGUS_API"
    )

    scan_level_recalculation_interval: int = Field(
        60, description="Interval in seconds of the periodic task that recalculates scan levels"
    )
    bits_enabled: Set[str] = Field(set(), example="{'port-classification-bit'}", description="Explicitly enabled bits")
    bits_disabled: Set[str] = Field(
        set(), example="{'port-classification-bit'}", description="Explicitly disabled bits"
    )

    span_export_grpc_endpoint: Optional[str] = Field(
        None, description="OpenTelemetry endpoint", env="SPAN_EXPORT_GRPC_ENDPOINT"
    )

    class Config:
        env_prefix = "OCTOPOES_"


DEFAULT_SCAN_LEVEL_FILTER = {scan_level for scan_level in ScanLevel}
DEFAULT_SCAN_PROFILE_TYPE_FILTER = {scan_profile_type for scan_profile_type in ScanProfileType}
DEFAULT_SEVERITY_FILTER = {severity for severity in RiskLevelSeverity}
DEFAULT_LIMIT = 50
DEFAULT_OFFSET = 0
QUEUE_NAME_OCTOPOES: str = "octopoes"
