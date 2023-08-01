from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import AmqpDsn, BaseSettings, Field, PostgresDsn

from bytes.models import EncryptionMiddleware, HashingAlgorithm, HashingRepositoryReference

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    secret: str = Field(..., description="Secret key used for generating Bytes' API JWT")
    username: str = Field(..., description="Username used for generating Bytes' API JWT")
    password: str = Field(..., description="Password used for generating Bytes' API JWT")
    queue_uri: AmqpDsn = Field("amqp://", description="KAT queue URI", env="QUEUE_URI")
    log_cfg: Path = Field(BASE_DIR / "dev.logging.conf", description="Path to the logging configuration file")

    db_uri: PostgresDsn = Field("postgresql://xx:xx@host:5432/bytes", description="Bytes Postgres DB URI")
    data_dir: Path = Field("/data", description="Directory where Bytes stores its data")

    log_file: str = Field("bytes.log", description="Log file name and extension")
    access_token_expire_minutes: float = Field(15.0, description="Access token expiration time in minutes")
    folder_permission: str = Field("740", description="Unix file system permission for folders")
    file_permission: str = Field("640", description="Unix file system permission for files")

    hashing_algorithm: HashingAlgorithm = Field(
        HashingAlgorithm.SHA512, description="Hashing algorithm used in Bytes", possible_values=["sha512", "sha224"]
    )

    ext_hash_repository: HashingRepositoryReference = Field(
        HashingRepositoryReference.IN_MEMORY,
        description="Encryption middleware used in Bytes",
        possible_values=["IN_MEMORY", "PASTEBIN", "RFC3161"],
    )
    pastebin_api_dev_key: str = Field(
        None, description="API key for Pastebin. Required when using PASTEBIN hashing repository."
    )
    rfc3161_provider: str = Field(
        None, description="URL of the RFC3161 provider. Required when using RFC3161 hashing repository."
    )
    rfc3161_cert_file: Path = Field(
        None,
        description="Path to the certificate of the RFC3161 provider. Required when using RFC3161 hashing repository.",
    )

    encryption_middleware: EncryptionMiddleware = Field(
        EncryptionMiddleware.IDENTITY,
        description="Encryption middleware used in Bytes",
        possible_values=["IDENTITY", "NACL_SEALBOX"],
    )
    private_key_b64: str = Field(
        None,
        description="Private key for Bytes' storage in base64 format. "
        "Required when using NACL_SEALBOX encryption middleware.",
    )
    public_key_b64: str = Field(
        None,
        description="Public key for Bytes' storage in base64 format. "
        "Required when using NACL_SEALBOX encryption middleware.",
    )

    metrics_ttl_seconds: int = Field(300, description="Time to live for metrics in seconds")

    span_export_grpc_endpoint: Optional[str] = Field(
        None, description="OpenTelemetry endpoint", env="SPAN_EXPORT_GRPC_ENDPOINT"
    )

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
