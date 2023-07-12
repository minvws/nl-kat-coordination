from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    debug: bool = Field(False, env="SCHEDULER_DEBUG")
    log_cfg: str = Field(
        str(Path(__file__).parent.parent.parent / "logging.json"),
        env="SCHEDULER_LOG_CFG",
    )

    # Server settings
    api_host: str = Field("0.0.0.0", env="SCHEDULER_API_HOST")
    api_port: int = Field(8000, env="SCHEDULER_API_PORT")

    # Application settings
    boefje_populate: bool = Field(False, env="SCHEDULER_BOEFJE_POPULATE")
    normalizer_populate: bool = Field(True, env="SCHEDULER_NORMALIZER_POPULATE")
    katalogus_cache_ttl: int = Field(30, env="SCHEDULER_KATALOGUS_CACHE_TTL")
    monitor_organisations_interval: int = Field(60, env="SCHEDULER_MONITOR_ORGANISATIONS_INTERVAL")
    octopoes_request_timeout: int = Field(10, env="SCHEDULER_OCTOPOES_REQUEST_TIMEOUT")

    # External services settings
    host_katalogus: str = Field(..., env="KATALOGUS_API")
    host_bytes: str = Field(..., env="BYTES_API")
    host_bytes_user: str = Field(..., env="BYTES_USERNAME")
    host_bytes_password: str = Field(..., env="BYTES_PASSWORD")
    host_octopoes: str = Field(..., env="OCTOPOES_API")
    host_mutation: str = Field(..., env="SCHEDULER_RABBITMQ_DSN")
    host_raw_data: str = Field(..., env="SCHEDULER_RABBITMQ_DSN")
    queue_prefetch_count: int = Field(100, env="SCHEDULER_QUEUE_PREFETCH_COUNT")
    host_normalizer_meta: str = Field(..., env="SCHEDULER_RABBITMQ_DSN")
    span_export_grpc_endpoint: Optional[str] = Field(None, env="SPAN_EXPORT_GRPC_ENDPOINT")

    # Queue settings (0 is infinite)
    pq_maxsize: int = Field(1000, env="SCHEDULER_PQ_MAXSIZE")
    pq_populate_interval: int = Field(60, env="SCHEDULER_PQ_INTERVAL")
    pq_populate_grace_period: int = Field(86400, env="SCHEDULER_PQ_GRACE")
    pq_populate_max_random_objects: int = Field(50, env="SCHEDULER_PQ_MAX_RANDOM_OBJECTS")

    # Database settings
    database_dsn: str = Field(..., env="SCHEDULER_DB_DSN")
