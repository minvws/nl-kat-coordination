from __future__ import annotations

import os
from pathlib import Path

from pydantic import AnyHttpUrl, Field, conint
from pydantic_settings import BaseSettings, SettingsConfigDict

from octopoes.models import ScanLevel, ScanProfileType
from octopoes.models.ooi.findings import RiskLevelSeverity

BASE_DIR: Path = Path(__file__).parent.parent.parent.resolve()

# Set base dir to something generic when compiling environment docs
if os.getenv("DOCS"):
    BASE_DIR = Path("../../../")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # External services settings
    xtdb_uri: AnyHttpUrl = Field(
        ..., examples=["http://xtdb:3000"], description="XTDB API", validation_alias="XTDB_URI"
    )

    scan_level_recalculation_interval: int = Field(
        60, description="Interval in seconds of the periodic task that recalculates scan levels"
    )
    schedule_interval: int = Field(60, description="Schedule interval for boefjes")
    grace_period: int = Field(1440, description="Grace period for boefjes in minutes")
    bits_enabled: set[str] = Field(set(), examples=['["port-common"]'], description="Explicitly enabled bits")
    bits_disabled: set[str] = Field(
        set(), examples=['["port-classification-ip"]'], description="Explicitly disabled bits"
    )
    scan_profile_whitelist: dict[str, conint(strict=True, ge=0, le=4)] = Field(  # type: ignore
        default_factory=dict,
        description="Whitelist for normalizer ids allowed to produce scan profiles, including a maximum level.",
        examples=['{"kat_external_db_normalize": 3, "kat_dns_normalize": 1}'],
    )
    outgoing_request_timeout: int = Field(30, description="Timeout for outgoing HTTP requests")

    workers: int = Field(4, description="Number of Octopoes Celery workers")

    model_config = SettingsConfigDict(env_prefix="OCTOPOES_")


DEFAULT_SCAN_LEVEL_FILTER = {scan_level for scan_level in ScanLevel}
DEFAULT_SCAN_PROFILE_TYPE_FILTER = {scan_profile_type for scan_profile_type in ScanProfileType}
DEFAULT_SEVERITY_FILTER = {severity for severity in RiskLevelSeverity}
DEFAULT_LIMIT = 50
DEFAULT_OFFSET = 0
QUEUE_NAME_OCTOPOES = "octopoes"
GATHER_BIT_METRICS = False
