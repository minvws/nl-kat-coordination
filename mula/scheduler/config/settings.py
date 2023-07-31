from pathlib import Path
from typing import Optional

from pydantic import AmqpDsn, BaseSettings, Field, PostgresDsn


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    debug: bool = Field(False, env="DEBUG")
    log_cfg: str = Field(str(Path(__file__).parent.parent.parent / "logging.json"))

    # Server settings
    api_host: str = Field("0.0.0.0", description="Host to bind the scheduler to")
    api_port: int = Field(8000, description="Host port to bind the scheduler to")

    # Application settings
    katalogus_cache_ttl: int = Field(30, description="Katalogus cache TTL in seconds")
    monitor_organisations_interval: int = Field(60, description="Monitor organisations interval in seconds")
    octopoes_request_timeout: int = Field(10, description="Octopoes request timeout in seconds")

    # External services settings
    host_katalogus: str = Field(..., env="KATALOGUS_API", description="Katalogus API URL")
    host_bytes: str = Field(..., env="BYTES_API", description="Bytes API URL")
    host_bytes_user: str = Field("test", description="Bytes JWT login username", env="BYTES_USERNAME")
    host_bytes_password: str = Field("secret", description="Bytes JWT login password", env="BYTES_PASSWORD")
    host_octopoes: str = Field(..., env="OCTOPOES_API", description="Octopoes API URL")

    queue_prefetch_count: int = Field(100)
    host_mutation: AmqpDsn = Field("amqp://", description="KAT queue URI", env="QUEUE_URI")
    host_raw_data: AmqpDsn = Field("amqp://", description="KAT queue URI", env="QUEUE_URI")
    host_normalizer_meta: AmqpDsn = Field("amqp://", description="KAT queue URI", env="QUEUE_URI")

    span_export_grpc_endpoint: Optional[str] = Field(None, env="SPAN_EXPORT_GRPC_ENDPOINT")

    # Queue settings (0 is infinite)
    pq_maxsize: int = Field(1000, description="Priority queue max size")
    pq_populate_interval: int = Field(60, description="Priority queue populate interval in seconds")
    pq_populate_grace_period: int = Field(86400, description="Priority queue populate grace period in seconds")
    pq_populate_max_random_objects: int = Field(50, description="Priority queue populate max random objects")

    # Database settings
    db_uri: PostgresDsn = Field("postgresql://xx:xx@host:5432/scheduler", description="Scheduler Postgres DB URI")

    class Config:
        env_prefix = "SCHEDULER_"
