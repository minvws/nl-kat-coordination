import os
from pathlib import Path

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    debug: bool = Field(False, env="SCHEDULER_DEBUG")
    log_cfg: str = Field(
        os.path.join(Path(__file__).parent.parent.parent, "logging.json"),
        env="SCHEDULER_LOG_CFG",
    )

    # Server settings
    api_host: str = Field("0.0.0.0", env="SCHEDULER_API_HOST")
    api_port: int = Field(8000, env="SCHEDULER_API_PORT")

    # Application settings
    boefje_populate: bool = Field(False, env="SCHEDULER_BOEFJE_POPULATE")
    normalizer_populate: bool = Field(True, env="SCHEDULER_NORMALIZER_POPULATE")

    # External services settings
    host_katalogus: str = Field(..., env="KATALOGUS_API")
    host_bytes: str = Field(..., env="BYTES_API")
    host_bytes_user: str = Field(..., env="BYTES_USERNAME")
    host_bytes_password: str = Field(..., env="BYTES_PASSWORD")
    host_octopoes: str = Field(..., env="OCTOPOES_API")
    host_scan_profile: str = Field(..., env="SCHEDULER_RABBITMQ_DSN")
    host_raw_data: str = Field(..., env="SCHEDULER_RABBITMQ_DSN")

    # Queue settings (0 is infinite)
    pq_maxsize: int = Field(1000, env="SHEDULER_PQ_MAXSIZE")
    pq_populate_interval: int = Field(60, env="SHEDULER_PQ_INTERVAL")
    pq_populate_grace_period: int = Field(86400, env="SHEDULER_PQ_GRACE")

    # Dispatcher settings
    dsp_interval: int = Field(5, env="SHEDULER_DSP_INTERVAL")
    dsp_broker_url: str = Field(..., env="SCHEDULER_DSP_BROKER_URL")
