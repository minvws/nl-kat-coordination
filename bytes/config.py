from pathlib import Path
from typing import Optional

from pydantic import BaseSettings

from bytes.models import HashingAlgorithm, HashingRepositoryReference, EncryptionMiddleware

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    secret: str
    bytes_username: str
    bytes_password: str
    queue_uri: Optional[str]
    log_cfg: Path = BASE_DIR / "dev.logging.conf"

    bytes_db_uri: str
    bytes_data_dir: Optional[str]

    bytes_log_file: str = "bytes.log"
    access_token_expire_minutes: float = 15.0
    bytes_folder_permission: str = "740"
    bytes_file_permission: str = "640"

    hashing_algorithm: HashingAlgorithm = HashingAlgorithm.SHA512

    ext_hash_repository: HashingRepositoryReference = HashingRepositoryReference.IN_MEMORY
    pastebin_api_dev_key: str = ""
    rfc3161_provider: Optional[str]
    rfc3161_cert_file: Optional[Path]

    encryption_middleware: EncryptionMiddleware = EncryptionMiddleware.NACL_SEALBOX
    kat_private_key_b64: str = ""
    vws_public_key_b64: str = ""


settings = Settings()


def get_bytes_data_directory() -> Path:
    if settings.bytes_data_dir:
        return Path(settings.bytes_data_dir)

    return Path(BASE_DIR) / "bytes-data"


def has_pastebin_key() -> bool:
    return settings.pastebin_api_dev_key != ""
