from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import AnyHttpUrl, BaseSettings, PostgresDsn


class RuntimeConfiguration(Enum):
    LOCAL = "local"


class Settings(BaseSettings):
    base_dir: Path = Path(__file__).parent.resolve()
    log_cfg: Path = Path(__file__).parent / "logging.json"  # Follow-up ticket to make logging the same for all modules?

    # Worker configuration
    pool_size: int = 2
    poll_interval: float = 10.0

    # Queue configuration
    queue_uri: str = "amqp://"

    # Runtime configuration
    runtime: RuntimeConfiguration = RuntimeConfiguration.LOCAL

    enable_db: bool = True  # Why would someone disable the database?
    katalogus_db_uri: PostgresDsn = "postgresql://xx:xx@host:5432/katalogus"

    scheduler_api: AnyHttpUrl = "http://localhost:8004"

    katalogus_api: AnyHttpUrl = "http://localhost:8003"

    octopoes_api: AnyHttpUrl = "http://localhost:8001"

    bytes_api: AnyHttpUrl = "http://localhost:8002"
    bytes_username: str = "test"
    bytes_password: str = "secret"

    span_export_grpc_endpoint: Optional[str] = None

    remote_ns: str = "8.8.8.8"  # Why do we default to Google DNS?


settings = Settings()
