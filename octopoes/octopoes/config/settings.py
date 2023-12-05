from __future__ import annotations

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple, Type

from pydantic import AmqpDsn, AnyHttpUrl, Field, FilePath
from pydantic_settings import BaseSettings, EnvSettingsSource, PydanticBaseSettingsSource, SettingsConfigDict

from octopoes.models import ScanLevel, ScanProfileType
from octopoes.models.ooi.findings import RiskLevelSeverity

BASE_DIR: Path = Path(__file__).parent.parent.parent.resolve()

# Set base dir to something generic when compiling environment docs
if os.getenv("DOCS"):
    BASE_DIR = Path("../../../")


class XTDBType(Enum):
    CRUX = "crux"
    XTDB = "xtdb"
    XTDB_MULTINODE = "xtdb-multinode"


class BackwardsCompatibleEnvSettings(EnvSettingsSource):
    backwards_compatibility_mapping = {
        "LOG_CFG": "OCTOPOES_LOG_CFG",
        "XTDB_TYPE": "OCTOPOES_XTDB_TYPE",
    }

    def __call__(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        env_vars = {k.lower(): v for k, v in os.environ.items()}
        env_prefix = self.settings_cls.model_config.get("env_prefix", "").lower()

        for old_name, new_name in self.backwards_compatibility_mapping.items():
            old_name, new_name = old_name.lower(), new_name.lower()

            # New variable not explicitly set through env,
            # ...but old variable has been explicitly set through env
            if new_name not in env_vars and old_name in env_vars:
                logging.warning("Deprecation: %s is deprecated, use %s instead", old_name.upper(), new_name.upper())
                d[new_name[len(env_prefix) :]] = env_vars[old_name]

        return d


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    log_cfg: FilePath = Field(BASE_DIR / "logging.yml", description="Path to the logging configuration file")

    # External services settings
    queue_uri: AmqpDsn = Field(..., examples=["amqp://"], description="KAT queue URI", validation_alias="QUEUE_URI")
    xtdb_uri: AnyHttpUrl = Field(
        ..., examples=["http://crux:3000"], description="XTDB API", validation_alias="XTDB_URI"
    )
    xtdb_type: XTDBType = Field(
        XTDBType.XTDB_MULTINODE,
        description="Determines how Octopoes will format documents' primary in serialization (crux.db/id vs xt/id)",
        possible_values=["crux", "xtdb", "xtdb-multinode"],
    )

    katalogus_api: AnyHttpUrl = Field(
        ..., examples=["http://localhost:8003"], description="Katalogus API URL", validation_alias="KATALOGUS_API"
    )

    scan_level_recalculation_interval: int = Field(
        60, description="Interval in seconds of the periodic task that recalculates scan levels"
    )
    bits_enabled: Set[str] = Field(set(), examples=['["port-common"]'], description="Explicitly enabled bits")
    bits_disabled: Set[str] = Field(
        set(), examples=['["port-classification-ip"]'], description="Explicitly disabled bits"
    )

    span_export_grpc_endpoint: Optional[AnyHttpUrl] = Field(
        None, description="OpenTelemetry endpoint", validation_alias="SPAN_EXPORT_GRPC_ENDPOINT"
    )

    model_config = SettingsConfigDict(env_prefix="OCTOPOES_")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        backwards_compatible_settings = BackwardsCompatibleEnvSettings(settings_cls)
        return env_settings, init_settings, file_secret_settings, backwards_compatible_settings


DEFAULT_SCAN_LEVEL_FILTER = {scan_level for scan_level in ScanLevel}
DEFAULT_SCAN_PROFILE_TYPE_FILTER = {scan_profile_type for scan_profile_type in ScanProfileType}
DEFAULT_SEVERITY_FILTER = {severity for severity in RiskLevelSeverity}
DEFAULT_LIMIT = 50
DEFAULT_OFFSET = 0
QUEUE_NAME_OCTOPOES: str = "octopoes"
