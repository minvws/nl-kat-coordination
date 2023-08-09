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
    katalogus_cache_ttl: int = Field(30, env="SCHEDULER_KATALOGUS_CACHE_TTL")
    monitor_organisations_interval: int = Field(60, env="SCHEDULER_MONITOR_ORGANISATIONS_INTERVAL")
    octopoes_request_timeout: int = Field(10, env="SCHEDULER_OCTOPOES_REQUEST_TIMEOUT")
    rabbitmq_prefetch_count: int = Field(100, env="SCHEDULER_RABBITMQ_PREFETCH_COUNT")

    # External services
    host_katalogus: str = Field(..., env="SCHEDULER_KATALOGUS_URL")
    host_bytes: str = Field(..., env="SCHEDULER_BYTES_URL")
    host_bytes_user: str = Field(..., env="SCHEDULER_BYTES_USERNAME")
    host_bytes_password: str = Field(..., env="SCHEDULER_BYTES_PASSWORD")
    host_octopoes: str = Field(..., env="SCHEDULER_OCTOPOES_URL")
    host_mutation: str = Field(..., env="SCHEDULER_RABBITMQ_DSN")
    host_raw_data: str = Field(..., env="SCHEDULER_RABBITMQ_DSN")
    host_metrics: Optional[str] = Field(None, env="SCHEDULER_METRICS_URL")

    # Queue settings (0 is infinite)
    pq_maxsize: int = Field(1000, env="SCHEDULER_PQ_MAXSIZE")
    pq_populate_interval: int = Field(60, env="SCHEDULER_PQ_INTERVAL")
    pq_populate_grace_period: int = Field(86400, env="SCHEDULER_PQ_GRACE")
    pq_populate_max_random_objects: int = Field(50, env="SCHEDULER_PQ_MAX_RANDOM_OBJECTS")

    # Database settings
    database_dsn: str = Field(..., env="SCHEDULER_DB_DSN")
