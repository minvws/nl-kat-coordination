from pathlib import Path
from typing import Optional

from pydantic import AmqpDsn, AnyHttpUrl, BaseSettings, Field, IPvAnyAddress, PostgresDsn


class Settings(BaseSettings):
    base_dir: Path = Field(Path(__file__).parent.resolve())
    log_cfg: Path = Field(Path(__file__).parent / "logging.json", description="Path to the logging configuration file")

    # Worker configuration
    pool_size: int = Field(2, description="Number of workers to run per queue")
    poll_interval: float = Field(10.0, description="Time to wait before polling for tasks when all queues are empty")
    worker_heartbeat: float = Field(1.0, description="Seconds to wait before checking the workers when queues are full")

    remote_ns: IPvAnyAddress = Field(
        "1.1.1.1", description="Name server used for remote DNS resolution in the boefje runner"
    )

    # Queue configuration
    queue_uri: AmqpDsn = Field(..., description="KAT queue URI", example="amqp://", env="QUEUE_URI")

    katalogus_db_uri: PostgresDsn = Field(
        ...,
        example="postgresql://xx:xx@host:5432/katalogus",
        description="Katalogus Postgres DB URI",
        env="KATALOGUS_DB_URI",
    )

    scheduler_api: AnyHttpUrl = Field(
        ..., example="http://localhost:8004", description="Mula API URL", env="SCHEDULER_API"
    )
    katalogus_api: AnyHttpUrl = Field(
        ..., example="http://localhost:8003", description="Katalogus API URL", env="KATALOGUS_API"
    )
    octopoes_api: AnyHttpUrl = Field(
        ..., example="http://localhost:8001", description="Octopoes API URL", env="OCTOPOES_API"
    )

    bytes_api: AnyHttpUrl = Field(..., example="http://localhost:8002", description="Bytes API URL", env="BYTES_API")
    bytes_username: str = Field(..., example="test", description="Bytes JWT login username", env="BYTES_USERNAME")
    bytes_password: str = Field(..., example="secret", description="Bytes JWT login password", env="BYTES_PASSWORD")

    span_export_grpc_endpoint: Optional[AnyHttpUrl] = Field(
        None, description="OpenTelemetry endpoint", env="SPAN_EXPORT_GRPC_ENDPOINT"
    )

    class Config:
        env_prefix = "BOEFJES_"
