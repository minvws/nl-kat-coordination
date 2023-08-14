import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pydantic import AmqpDsn, AnyHttpUrl, BaseSettings, Field, IPvAnyAddress, PostgresDsn
from pydantic.env_settings import SettingsSourceCallable

BASE_DIR: Path = Path(__file__).parent.parent.parent.resolve()

# Set base dir to something generic when compiling environment docs
if os.getenv("DOCS"):
    BASE_DIR = Path("../../../")


class BackwardsCompatibleEnvSettings:
    backwards_compatibility_mapping = {
        "SCHEDULER_RABBITMQ_DSN": "QUEUE_URI",
        "SCHEDULER_DB_DSN": "SCHEDULER_DB_URI",
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
    """Application settings loaded from environment variables."""

    # Application settings
    debug: bool = Field(False, description="Enables/disables global debugging mode", env="DEBUG")
    log_cfg: Path = Field(BASE_DIR / "logging.json", description="Path to the logging configuration file")

    # Server settings
    api_host: IPvAnyAddress = Field("0.0.0.0", description="Host address of the scheduler api server")
    api_port: int = Field(8000, description="Host api server port")

    # Application settings
    katalogus_cache_ttl: int = Field(30, description="The lifetime of the katalogus cache in seconds")
    monitor_organisations_interval: int = Field(
        60,
        description="Interval in seconds of the execution of the "
        "`monitor_organisations` method of the scheduler application"
        " to check newly created or removed organisations from katalogus. "
        "It updates the organisations, their plugins, and the creation of their schedulers.",
    )
    octopoes_request_timeout: int = Field(10, description="The timeout in seconds for the requests to the octopoes api")

    # External services settings
    host_katalogus: AnyHttpUrl = Field(
        ..., example="http://localhost:8003", env="KATALOGUS_API", description="Katalogus API URL"
    )
    host_bytes: AnyHttpUrl = Field(..., example="http://localhost:8004", env="BYTES_API", description="Bytes API URL")
    host_bytes_user: str = Field(..., example="test", description="Bytes JWT login username", env="BYTES_USERNAME")
    host_bytes_password: str = Field(
        ..., example="secret", description="Bytes JWT login password", env="BYTES_PASSWORD"
    )
    host_octopoes: AnyHttpUrl = Field(
        ..., example="http://localhost:8001", env="OCTOPOES_API", description="Octopoes API URL"
    )

    queue_prefetch_count: int = Field(
        100,
        description="RabbitMQ prefetch_count for `channel.basic_qos()`, "
        "which is the number of unacknowledged messages on a channel. "
        "Also see https://www.rabbitmq.com/consumer-prefetch.html",
    )
    host_mutation: AmqpDsn = Field(
        ..., example="amqp://", description="KAT queue URI for host mutations", env="QUEUE_URI"
    )
    host_raw_data: AmqpDsn = Field(
        ..., example="amqp://", description="KAT queue URI for host raw data", env="QUEUE_URI"
    )
    host_normalizer_meta: AmqpDsn = Field(
        ..., example="amqp://", description="KAT queue URI for host normalizer meta", env="QUEUE_URI"
    )

    # Queue settings (0 is infinite)
    pq_maxsize: int = Field(1000, description="How many items a priority queue can hold")
    pq_populate_interval: int = Field(
        60,
        description="Interval in seconds of the "
        "execution of the `populate_queue` method of the `scheduler.Scheduler` class",
    )
    pq_populate_grace_period: int = Field(
        86400, description="Grace period of when a job is considered to be running again (in seconds),"
    )
    pq_populate_max_random_objects: int = Field(
        50, description="The maximum number of random objects that can be added to the priority queue, per call"
    )

    # Database settings
    db_uri: PostgresDsn = Field(
        ..., example="postgresql://xx:xx@host:5432/scheduler", description="Scheduler Postgres DB URI"
    )

    span_export_grpc_endpoint: Optional[AnyHttpUrl] = Field(
        None, description="OpenTelemetry endpoint", env="SPAN_EXPORT_GRPC_ENDPOINT"
    )

    class Config:
        env_prefix = "SCHEDULER_"

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> Tuple[SettingsSourceCallable, ...]:
            backwards_compatible_settings = BackwardsCompatibleEnvSettings()
            return env_settings, init_settings, file_secret_settings, backwards_compatible_settings
