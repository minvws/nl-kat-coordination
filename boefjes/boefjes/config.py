import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Type

from pydantic import AmqpDsn, AnyHttpUrl, Field, FilePath, IPvAnyAddress, PostgresDsn
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from pydantic_settings.sources import EnvSettingsSource

BASE_DIR: Path = Path(__file__).parent.resolve()

# Set base dir to something generic when compiling environment docs
if os.getenv("DOCS"):
    BASE_DIR = Path("../")


class BackwardsCompatibleEnvSettings(EnvSettingsSource):
    backwards_compatibility_mapping = {
        "LOG_CFG": "BOEFJES_LOG_CFG",
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
    log_cfg: FilePath = Field(BASE_DIR / "logging.json", description="Path to the logging configuration file")

    # Worker configuration
    pool_size: int = Field(2, description="Number of workers to run per queue")
    poll_interval: float = Field(10.0, description="Time to wait before polling for tasks when all queues are empty")
    worker_heartbeat: float = Field(1.0, description="Seconds to wait before checking the workers when queues are full")

    remote_ns: IPvAnyAddress = Field(
        "1.1.1.1", description="Name server used for remote DNS resolution in the boefje runner"
    )

    # Queue configuration
    queue_uri: AmqpDsn = Field(..., description="KAT queue URI", examples=["amqp://"], validation_alias="QUEUE_URI")

    katalogus_db_uri: PostgresDsn = Field(
        ...,
        examples=["postgresql://xx:xx@host:5432/katalogus"],
        description="Katalogus Postgres DB URI",
        validation_alias="KATALOGUS_DB_URI",
    )

    scheduler_api: AnyHttpUrl = Field(
        ..., examples=["http://localhost:8004"], description="Mula API URL", validation_alias="SCHEDULER_API"
    )
    katalogus_api: AnyHttpUrl = Field(
        ..., examples=["http://localhost:8003"], description="Katalogus API URL", validation_alias="KATALOGUS_API"
    )
    octopoes_api: AnyHttpUrl = Field(
        ..., examples=["http://localhost:8001"], description="Octopoes API URL", validation_alias="OCTOPOES_API"
    )
    boefje_api: AnyHttpUrl = Field(
        ..., examples=["http://boefje:8000"], description="Boefje API URL", validation_alias="BOEFJE_API"
    )
    # Boefje server settings
    boefje_api_host: str = Field(
        "0.0.0.0",
        description="Host address of the Boefje API server",
    )
    boefje_api_port: int = Field(
        8000,
        description="Host port of the Boefje API server",
    )

    bytes_api: AnyHttpUrl = Field(
        ..., examples=["http://localhost:8002"], description="Bytes API URL", validation_alias="BYTES_API"
    )
    bytes_username: str = Field(
        ..., examples=["test"], description="Bytes JWT login username", validation_alias="BYTES_USERNAME"
    )
    bytes_password: str = Field(
        ..., examples=["secret"], description="Bytes JWT login password", validation_alias="BYTES_PASSWORD"
    )

    span_export_grpc_endpoint: Optional[AnyHttpUrl] = Field(
        None, description="OpenTelemetry endpoint", validation_alias="SPAN_EXPORT_GRPC_ENDPOINT"
    )

    model_config = SettingsConfigDict(env_prefix="BOEFJES_")

    # TODO[pydantic]: We couldn't refactor this class, please create the `model_config` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-config for more information.
    # class Config:
    #
    #     @classmethod
    #     def customise_sources(
    #         cls,
    #         init_settings: SettingsSourceCallable,
    #         env_settings: SettingsSourceCallable,
    #         file_secret_settings: SettingsSourceCallable,
    #     ) -> Tuple[SettingsSourceCallable, ...]:

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


# Do not initialize the settings module when compiling environment docs
if not os.getenv("DOCS"):
    settings = Settings()
