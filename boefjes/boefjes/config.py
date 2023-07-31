from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import AmqpDsn, AnyHttpUrl, BaseSettings, Field, PostgresDsn


class RuntimeConfiguration(Enum):
    LOCAL = "local"


class Settings(BaseSettings):
    base_dir: Path = Path(__file__).parent.resolve()
    log_cfg: Path = Path(__file__).parent / "logging.json"

    # Worker configuration
    pool_size: int = Field(2, description="")
    poll_interval: float = Field(10.0, description="")
    worker_heartbeat: float = Field(1.0, description="Seconds to wait before checking the workers when queues are full")

    remote_ns: str = Field("1.1.1.1", description="Name server used for remote DNS resolution in the boefje runner")

    # Queue configuration
    queue_uri: AmqpDsn = Field("amqp://", description="KAT queue URI", env="QUEUE_URI")

    # Runtime configuration
    runtime: RuntimeConfiguration = RuntimeConfiguration.LOCAL

    katalogus_db_uri: PostgresDsn = Field(
        "postgresql://xx:xx@host:5432/katalogus", description="Katalogus Postgres DB URI", env="KATALOGUS_DB"
    )

    scheduler_api: AnyHttpUrl = Field("http://localhost:8004", description="Mula API URL", env="SCHEDULER_API")
    katalogus_api: AnyHttpUrl = Field("http://localhost:8003", description="Katalogus API URL", env="KATALOGUS_API")
    octopoes_api: AnyHttpUrl = Field("http://localhost:8001", description="Octopoes API URL", env="OCTOPOES_API")

    bytes_api: AnyHttpUrl = Field("http://localhost:8002", description="Bytes API URL", env="BYTES_API")
    bytes_username: str = Field("test", description="Bytes JWT login username", env="BYTES_USERNAME")
    bytes_password: str = Field("secret", description="Bytes JWT login password", env="BYTES_PASSWORD")

    span_export_grpc_endpoint: Optional[str] = Field(None, env="SPAN_EXPORT_GRPC_ENDPOINT")

    class Config:
        env_prefix = "BOEFJES_"


settings = Settings()
