from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    model_config = SettingsConfigDict(env_prefix="SCHEDULER_")

    # Application settings
    debug: bool = Field(False, env="SCHEDULER_DEBUG")
    log_cfg: str = Field(
        str(Path(__file__).parent.parent.parent / "logging.json"),
        env="SCHEDULER_LOG_CFG",
    )

    # Server settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Application settings
    katalogus_cache_ttl: int = 30
    monitor_organisations_interval: int = 60
    octopoes_request_timeout: int = 10
    rabbitmq_prefetch_count: int = 100

    # External services
    host_katalogus: str = ""
    host_bytes: str = ""
    host_bytes_user: str = ""
    host_bytes_password: str = ""
    host_octopoes: str = ""
    host_mutation: str = ""
    host_raw_data: str = ""
    host_metrics: str = ""

    # Queue settings (0 is infinite)
    pq_maxsize: int = 1000
    pq_interval: int = 60
    pq_grace: int = 86400
    pq_max_random_objects: int = 50

    # Database settings
    db_dsn: str = ""
