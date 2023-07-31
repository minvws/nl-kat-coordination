from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, Field, PostgresDsn

from bytes.models import EncryptionMiddleware, HashingAlgorithm, HashingRepositoryReference

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    secret: str
    username: str
    password: str
    queue_uri: Optional[str]
    log_cfg: Path = BASE_DIR / "dev.logging.conf"

    db_uri: PostgresDsn = Field("postgresql://xx:xx@host:5432/bytes", description="Bytes Postgres DB URI")
    data_dir: Path = Field("/data", description="Directory where Bytes stores its data")

    log_file: str = Field("bytes.log", description="Log file name and extension")
    access_token_expire_minutes: float = Field(15.0, description="Access token expiration time in minutes")
    folder_permission: str = Field("740", description="Unix file system permission for folders")
    file_permission: str = Field("640", description="Unix file system permission for files")

    hashing_algorithm: HashingAlgorithm = HashingAlgorithm.SHA512

    ext_hash_repository: HashingRepositoryReference = HashingRepositoryReference.IN_MEMORY
    pastebin_api_dev_key: str = Field("", description="API key for Pastebin")
    rfc3161_provider: Optional[str] = Field("", description="URL of the RFC3161 provider")
    rfc3161_cert_file: Optional[Path] = Field("", description="Path to the certificate of the RFC3161 provider")

    encryption_middleware: EncryptionMiddleware = EncryptionMiddleware.IDENTITY
    private_key_b64: str = Field("", description="Private key for Bytes' storage in base64 format")
    public_key_b64: str = Field("", description="Public key for Bytes' storage in base64 format")

    span_export_grpc_endpoint: Optional[str] = Field(None, env="SPAN_EXPORT_GRPC_ENDPOINT")
    metrics_ttl_seconds: int = Field(300, description="Time to live for metrics in seconds")

    class Config:
        env_prefix = "BYTES_"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def has_pastebin_key() -> bool:
    settings = get_settings()

    return bool(settings.pastebin_api_dev_key)


def has_rfc3161_provider() -> bool:
    settings = get_settings()

    return bool(settings.rfc3161_provider)
