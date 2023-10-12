import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Type

from pydantic import AmqpDsn, AnyHttpUrl, Field, PostgresDsn, fields
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

BASE_DIR: Path = Path(__file__).parent.parent.parent.resolve()

# Set base dir to something generic when compiling environment docs
if os.getenv("DOCS"):
    BASE_DIR = Path("../../../")


class BackwardsCompatibleEnvSettings(PydanticBaseSettingsSource):
    backwards_compatibility_mapping = {
        "SCHEDULER_RABBITMQ_DSN": "QUEUE_URI",
        "SCHEDULER_DB_DSN": "SCHEDULER_DB_URI",
    }

    def get_field_value(self, field: fields.FieldInfo, field_name: str) -> Tuple[Any, str, bool]:
        return super().get_field_value(field, field_name)

    def __call__(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        env_vars = {k.lower(): v for k, v in os.environ.items()}
        env_prefix = self.settings_cls.model_config.get("env_prefix").lower()

        for old_name, new_name in self.backwards_compatibility_mapping.items():
            old_name, new_name = old_name.lower(), new_name.lower()

            # New variable not explicitly set through env,
            # ...but old variable has been explicitly set through env
            if new_name not in env_vars and old_name in env_vars:
                logging.warning("Deprecation: %s is deprecated, use %s instead", old_name.upper(), new_name.upper())
                if new_name == "queue_uri":
                    d["QUEUE_URI"] = env_vars[old_name]
                else:
                    d[new_name[len(env_prefix) :]] = env_vars[old_name]

        return d


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="SCHEDULER_")

    # Application settings
    debug: bool = Field(
        False,
        alias="DEBUG",
        description="Enables/disables global debugging mode",
    )

    log_cfg: Path = Field(
        BASE_DIR / "logging.json",
        description="Path to the logging configuration file",
    )

    collect_metrics: bool = Field(
        False,
        description="Enables/disables the collection of metrics to be used with tools like Prometheus",
    )

    # Server settings
    api_host: str = Field(
        "0.0.0.0",
        description="Host address of the scheduler api server",
    )

    api_port: int = Field(
        8000,
        description="Host api server port",
    )

    # Application settings
    katalogus_cache_ttl: int = Field(
        30,
        description="The lifetime of the katalogus cache in seconds",
    )

    monitor_organisations_interval: int = Field(
        60,
        description="Interval in seconds of the execution of the "
        "`monitor_organisations` method of the scheduler application"
        " to check newly created or removed organisations from katalogus. "
        "It updates the organisations, their plugins, and the creation of "
        "their schedulers.",
    )

    octopoes_request_timeout: int = Field(
        10,
        description="The timeout in seconds for the requests to the octopoes api",
    )

    rabbitmq_prefetch_count: int = Field(
        100,
        description="RabbitMQ prefetch_count for `channel.basic_qos()`, "
        "which is the number of unacknowledged messages on a channel. "
        "Also see https://www.rabbitmq.com/consumer-prefetch.html",
    )

    # External services settings
    host_katalogus: AnyHttpUrl = Field(
        ...,
        example="http://localhost:8003",
        alias="KATALOGUS_API",
        description="Katalogus API URL",
    )

    host_bytes: AnyHttpUrl = Field(
        ...,
        example="http://localhost:8004",
        alias="BYTES_API",
        description="Bytes API URL",
    )

    host_bytes_user: str = Field(
        ...,
        example="test",
        alias="BYTES_USERNAME",
        description="Bytes JWT login username",
    )

    host_bytes_password: str = Field(
        ...,
        example="secret",
        alias="BYTES_PASSWORD",
        description="Bytes JWT login password",
    )

    host_octopoes: AnyHttpUrl = Field(
        ...,
        example="http://localhost:8001",
        alias="OCTOPOES_API",
        description="Octopoes API URL",
    )

    host_mutation: AmqpDsn = Field(
        ...,
        example="amqp://",
        alias="QUEUE_URI",
        description="KAT queue URI for host mutations",
    )

    host_raw_data: AmqpDsn = Field(
        ...,
        example="amqp://",
        alias="QUEUE_URI",
        description="KAT queue URI for host raw data",
    )

    host_metrics: Optional[AnyHttpUrl] = Field(
        None,
        alias="SPAN_EXPORT_GRPC_ENDPOINT",
        description="OpenTelemetry endpoint",
    )

    # Queue settings
    pq_maxsize: int = Field(
        1000,
        description="How many items a priority queue can hold (0 is infinite)",
    )

    pq_interval: int = Field(
        60,
        description="Interval in seconds of the execution of the `` method of the `scheduler.Scheduler` class",
    )

    pq_grace_period: int = Field(
        86400,
        description="Grace period of when a job is considered to be running again in seconds",
    )

    pq_max_random_objects: int = Field(
        50,
        description="The maximum number of random objects that can be added to the priority queue, per call",
    )

    # Database settings
    db_uri: PostgresDsn = Field(
        ..., example="postgresql://xx:xx@host:5432/scheduler", description="Scheduler Postgres DB URI"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            BackwardsCompatibleEnvSettings(settings_cls),
        )
