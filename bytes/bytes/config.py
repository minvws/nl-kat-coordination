import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pydantic import AmqpDsn, AnyHttpUrl, BaseSettings, DirectoryPath, Field, FilePath, PostgresDsn
from pydantic.env_settings import SettingsSourceCallable

from bytes.models import EncryptionMiddleware, HashingAlgorithm, HashingRepositoryReference

BASE_DIR: Path = Path(__file__).parent.parent.resolve()

# Set base dir to something generic when compiling environment docs
if os.getenv("DOCS"):
    BASE_DIR = Path("../../")


class BackwardsCompatibleEnvSettings:
    backwards_compatibility_mapping = {
        "SECRET": "BYTES_SECRET",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "BYTES_ACCESS_TOKEN_EXPIRE_MINUTES",
        "ENCRYPTION_MIDDLEWARE": "BYTES_ENCRYPTION_MIDDLEWARE",
        "LOG_CFG": "BYTES_LOG_CFG",
        "EXT_HASH_REPOSITORY": "BYTES_EXT_HASH_REPOSITORY",
        "EXT_HASH_SERVICE": "BYTES_EXT_HASH_REPOSITORY",
        "PASTEBIN_API_DEV_KEY": "BYTES_PASTEBIN_API_DEV_KEY",
        "HASHING_ALGORITHM": "BYTES_HASHING_ALGORITHM",
        "KAT_PRIVATE_KEY_B64": "BYTES_PRIVATE_KEY_B64",
        "VWS_PUBLIC_KEY_B64": "BYTES_PUBLIC_KEY_B64",
        "RFC3161_PROVIDER": "BYTES_RFC3161_PROVIDER",
        "RFC3161_CERT_FILE": "BYTES_RFC3161_CERT_FILE",
    }

    def __call__(self, settings: BaseSettings) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        env_vars = {k.lower(): v for k, v in os.environ.items()}
        env_prefix = settings.__config__.env_prefix.lower()

        for old_name, new_name in self.backwards_compatibility_mapping.items():
            old_name, new_name = old_name.lower(), new_name.lower()

            # New variable not explicitly set through env,
            # ...but old variable has been explicitly set through env
            if new_name not in env_vars and old_name in env_vars:
                logging.warning("Deprecation: %s is deprecated, use %s instead", old_name.upper(), new_name.upper())
                d[new_name[len(env_prefix) :]] = env_vars[old_name]

        # We previously accepted an empty value for this field
        if "rfc3161_provider" in d and not d["rfc3161_provider"]:
            del d["rfc3161_provider"]

        if "rfc3161_cert_file" in d and not d["rfc3161_cert_file"]:
            del d["rfc3161_cert_file"]

        return d


class Settings(BaseSettings):
    secret: str = Field(
        ...,
        example="bec4837fe5108205ce6cd1bc11735d4a220e253345e90619c6",
        description="Secret key used for generating Bytes' API JWT",
    )
    username: str = Field(..., example="test", description="Username used for generating Bytes' API JWT")
    password: str = Field(..., example="secret", description="Password used for generating Bytes' API JWT")
    queue_uri: AmqpDsn = Field(..., example="amqp://", description="KAT queue URI", env="QUEUE_URI")
    log_cfg: FilePath = Field(BASE_DIR / "dev.logging.conf", description="Path to the logging configuration file")

    db_uri: PostgresDsn = Field(..., example="postgresql://xx:xx@host:5432/bytes", description="Bytes Postgres DB URI")
    data_dir: DirectoryPath = Field(
        "/data",
        description="Root for all the data. "
        "A change means that you no longer have access to old data unless you move it!",
    )

    log_file: str = Field("bytes.log", description="Optional file with Bytes logs")
    access_token_expire_minutes: float = Field(15.0, description="Access token expiration time in minutes")
    folder_permission: str = Field(
        "740", description="Unix permission level on the folders Bytes creates to save raw files"
    )
    file_permission: str = Field("640", description="Unix permission level on the raw files themselves")

    hashing_algorithm: HashingAlgorithm = Field(
        HashingAlgorithm.SHA512, description="Hashing algorithm used in Bytes", possible_values=["sha512", "sha224"]
    )

    ext_hash_repository: HashingRepositoryReference = Field(
        HashingRepositoryReference.IN_MEMORY,
        description="Hashing repository used in Bytes (IN_MEMORY is a stub)",
        possible_values=["IN_MEMORY", "PASTEBIN", "RFC3161"],
    )
    pastebin_api_dev_key: str = Field(
        None, description="API key for Pastebin. Required when using PASTEBIN hashing repository."
    )
    rfc3161_provider: AnyHttpUrl = Field(
        None,
        example="https://freetsa.org/tsr",
        description="Timestamping. "
        "See https://github.com/trbs/rfc3161ng for a list of public providers and their certificates. "
        "Required when using RFC3161 hashing repository.",
    )
    rfc3161_cert_file: FilePath = Field(
        None,
        example="bytes/timestamping/certificates/freetsa.crt",
        description="Path to the certificate of the RFC3161 provider. Required when using RFC3161 hashing repository. "
        "`freetsa.crt` is included in the Bytes source code.",
    )

    encryption_middleware: EncryptionMiddleware = Field(
        EncryptionMiddleware.IDENTITY,
        description="Encryption middleware used in Bytes",
        possible_values=["IDENTITY", "NACL_SEALBOX"],
    )
    private_key_b64: str = Field(
        None,
        description="KATalogus NaCl Sealbox base-64 private key string. "
        "Required when using NACL_SEALBOX encryption middleware.",
    )
    public_key_b64: str = Field(
        None,
        description="KATalogus NaCl Sealbox base-64 public key string. "
        "Required when using NACL_SEALBOX encryption middleware.",
    )

    metrics_ttl_seconds: int = Field(
        300, description="The time to cache slow queries performed in the metrics endpoint"
    )

    span_export_grpc_endpoint: Optional[AnyHttpUrl] = Field(
        None, description="OpenTelemetry endpoint", env="SPAN_EXPORT_GRPC_ENDPOINT"
    )

    class Config:
        env_prefix = "BYTES_"

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> Tuple[SettingsSourceCallable, ...]:
            backwards_compatible_settings = BackwardsCompatibleEnvSettings()
            return env_settings, init_settings, file_secret_settings, backwards_compatible_settings


@lru_cache
def get_settings() -> Settings:
    return Settings()


def has_pastebin_key() -> bool:
    settings = get_settings()

    return bool(settings.pastebin_api_dev_key)


def has_rfc3161_provider() -> bool:
    settings = get_settings()

    return bool(settings.rfc3161_provider)
