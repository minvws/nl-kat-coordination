from pathlib import Path
from typing import Optional

from pydantic import AmqpDsn, BaseSettings, Field, PostgresDsn


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    debug: bool = Field(False, description="Enables/disables global debugging mode", env="DEBUG")
    log_cfg: str = Field(
        str(Path(__file__).parent.parent.parent / "logging.json"), description="Path to the logging configuration file"
    )

    # Server settings
    api_host: str = Field("0.0.0.0", description="Host to bind the scheduler to")
    api_port: int = Field(8000, description="Host port to bind the scheduler to")

    # Application settings
    katalogus_cache_ttl: int = Field(30, description="Katalogus cache TTL in seconds")
    monitor_organisations_interval: int = Field(
        60,
        description="Interval in seconds of the execution of the "
        "`monitor_organisations` method of the scheduler application"
        " to check newly created or removed organisations from katalogus. "
        "It updates the organisations, their plugins, and the creation of their schedulers.",
    )
    octopoes_request_timeout: int = Field(10, description="Octopoes request timeout in seconds")

    # External services settings
    host_katalogus: str = Field(
        ..., example="http://localhost:8003", env="KATALOGUS_API", description="Katalogus API URL"
    )
    host_bytes: str = Field(..., example="http://localhost:8004", env="BYTES_API", description="Bytes API URL")
    host_bytes_user: str = Field(..., example="test", description="Bytes JWT login username", env="BYTES_USERNAME")
    host_bytes_password: str = Field(
        ..., example="secret", description="Bytes JWT login password", env="BYTES_PASSWORD"
    )
    host_octopoes: str = Field(..., example="http://localhost:8001", env="OCTOPOES_API", description="Octopoes API URL")

    queue_prefetch_count: int = Field(100)
    host_mutation: AmqpDsn = Field(..., example="amqp://", description="KAT queue URI", env="QUEUE_URI")
    host_raw_data: AmqpDsn = Field(..., example="amqp://", description="KAT queue URI", env="QUEUE_URI")
    host_normalizer_meta: AmqpDsn = Field(..., example="amqp://", description="KAT queue URI", env="QUEUE_URI")

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
        50, description="Maximum number of random objects to be added to the priority queue"
    )

    # Database settings
    db_uri: PostgresDsn = Field(
        ..., example="postgresql://xx:xx@host:5432/scheduler", description="Scheduler Postgres DB URI"
    )

    span_export_grpc_endpoint: Optional[str] = Field(
        None, description="OpenTelemetry endpoint", env="SPAN_EXPORT_GRPC_ENDPOINT"
    )

    class Config:
        env_prefix = "SCHEDULER_"
