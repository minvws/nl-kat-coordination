from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, AnyHttpUrl, PostgresDsn


class Settings(BaseSettings):
    base_dir: Path = Path(__file__).parent.resolve()
    worker_concurrency: int = 10

    queue_name_boefjes: str = "boefjes"
    queue_name_normalizers: str = "normalizers"
    queue_uri: str = "amqp://"

    enable_db: bool = True
    katalogus_db_uri: PostgresDsn = "postgresql://xx:xx@host:5432/katalogus"

    katalogus_api: AnyHttpUrl = "http://localhost:8003"

    octopoes_api: AnyHttpUrl = "http://localhost:8001"

    bytes_api: AnyHttpUrl = "http://localhost:8002"
    bytes_username: str = "test"
    bytes_password: str = "secret"

    wp_scan_api: str = ""
    shodan_api: str = ""
    binaryedge_api: str = ""
    leakix_api: str = ""
    remote_ns: str = "8.8.8.8"

    lxd_endpoint: str = ""
    lxd_password: Optional[str] = None


settings = Settings()
