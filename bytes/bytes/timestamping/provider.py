from bytes.config import Settings
from bytes.models import HashingRepositoryReference
from bytes.repositories.hash_repository import HashRepository
from bytes.timestamping.in_memory import InMemoryHashRepository
from bytes.timestamping.pastebin import PastebinHashRepository
from bytes.timestamping.rfc3161 import RFC3161HashRepository


def create_hash_repository(settings: Settings) -> HashRepository:
    if settings.ext_hash_repository == HashingRepositoryReference.PASTEBIN:
        if not settings.pastebin_api_dev_key:
            raise ValueError("Cannot use the pastebin hashing service without a pastebin key")

        return PastebinHashRepository(settings.pastebin_api_dev_key)

    if settings.ext_hash_repository == HashingRepositoryReference.RFC3161:
        assert settings.rfc3161_cert_file and settings.rfc3161_provider, "RFC3161 service needs a url and a certificate"

        return RFC3161HashRepository(settings.rfc3161_cert_file.read_bytes(), settings.rfc3161_provider)

    return InMemoryHashRepository()
