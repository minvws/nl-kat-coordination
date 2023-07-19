from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings

from bytes.models import EncryptionMiddleware, HashingAlgorithm, HashingRepositoryReference

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    secret: str
    bytes_username: str
    bytes_password: str
    queue_uri: Optional[str]
    log_cfg: Path = BASE_DIR / "dev.logging.conf"  # Follow-up ticket to make logging the same for all modules?

    bytes_db_uri: str
    bytes_data_dir: Path = Path("/data")

    bytes_log_file: str = "bytes.log"
    access_token_expire_minutes: float = 15.0  # Which value should be the default and why?
    bytes_folder_permission: str = "740"
    bytes_file_permission: str = "640"

    hashing_algorithm: HashingAlgorithm = HashingAlgorithm.SHA512

    ext_hash_repository: HashingRepositoryReference = HashingRepositoryReference.IN_MEMORY
    pastebin_api_dev_key: str = ""
    rfc3161_provider: Optional[str]
    rfc3161_cert_file: Optional[Path]

    encryption_middleware: EncryptionMiddleware = EncryptionMiddleware.IDENTITY
    private_key_b64: str = ""
    public_key_b64: str = ""

    span_export_grpc_endpoint: Optional[str]
    bytes_metrics_ttl_seconds: int = 300  # Which value should be the default and why?


@lru_cache
def get_settings() -> Settings:
    return Settings()


def has_pastebin_key() -> bool:
    settings = get_settings()

    return bool(settings.pastebin_api_dev_key)


def has_rfc3161_provider() -> bool:
    settings = get_settings()

    return bool(settings.rfc3161_provider)
