import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pydantic import AmqpDsn, AnyHttpUrl, BaseSettings, Field, FilePath, IPvAnyAddress, PostgresDsn
from pydantic.env_settings import SettingsSourceCallable

BASE_DIR: Path = Path(__file__).parent.resolve()

# Set base dir to something generic when compiling environment docs
if os.getenv("DOCS"):
    BASE_DIR = Path("../")


class BackwardsCompatibleEnvSettings:
    backwards_compatibility_mapping = {
        "LOG_CFG": "BOEFJES_LOG_CFG",
    }

    def __call__(self, settings: BaseSettings) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        env_vars = {k.lower(): v for k, v in os.environ.items()}
        env_prefix = settings.__config__.env_prefix.lower()

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
    queue_uri: AmqpDsn = Field(..., description="KAT queue URI", example="amqp://", env="QUEUE_URI")

    katalogus_db_uri: PostgresDsn = Field(
        ...,
        example="postgresql://xx:xx@host:5432/katalogus",
        description="Katalogus Postgres DB URI",
        env="KATALOGUS_DB_URI",
    )

    scheduler_api: AnyHttpUrl = Field(
        ..., example="http://localhost:8004", description="Mula API URL", env="SCHEDULER_API"
    )
    katalogus_api: AnyHttpUrl = Field(
        ..., example="http://localhost:8003", description="Katalogus API URL", env="KATALOGUS_API"
    )
    octopoes_api: AnyHttpUrl = Field(
        ..., example="http://localhost:8001", description="Octopoes API URL", env="OCTOPOES_API"
    )
    boefje_api: AnyHttpUrl = Field(..., example="http://boefje:8000", description="Boefje API URL", env="BOEFJE_API")
    # Boefje server settings
    boefje_api_host: str = Field(
        "0.0.0.0",
        description="Host address of the Boefje API server",
    )
    boefje_api_port: int = Field(
        8000,
        description="Host port of the Boefje API server",
    )

    boefje_docker_network: str = Field(
        "bridge",
        description="Docker network to run Boefjes in",
        env="BOEFJE_DOCKER_NETWORK",
    )

    bytes_api: AnyHttpUrl = Field(..., example="http://localhost:8002", description="Bytes API URL", env="BYTES_API")
    bytes_username: str = Field(..., example="test", description="Bytes JWT login username", env="BYTES_USERNAME")
    bytes_password: str = Field(..., example="secret", description="Bytes JWT login password", env="BYTES_PASSWORD")

    span_export_grpc_endpoint: Optional[AnyHttpUrl] = Field(
        None, description="OpenTelemetry endpoint", env="SPAN_EXPORT_GRPC_ENDPOINT"
    )

    class Config:
        env_prefix = "BOEFJES_"

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> Tuple[SettingsSourceCallable, ...]:
            backwards_compatible_settings = BackwardsCompatibleEnvSettings()
            return env_settings, init_settings, file_secret_settings, backwards_compatible_settings


# Do not initialize the settings module when compiling environment docs
if not os.getenv("DOCS"):
    settings = Settings()
