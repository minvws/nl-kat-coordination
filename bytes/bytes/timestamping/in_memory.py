import uuid

from bytes.models import RetrievalLink, SecureHash
from bytes.repositories.hash_repository import HashRepository


class InMemoryHashRepository(HashRepository):
    def __init__(self, signing_provider_url: str | None = None) -> None:
        self.signing_provider_url = signing_provider_url  # Being able to set this to a string is useful for testing
        self.memory: dict[str, SecureHash] = {}

    def store(self, secure_hash: SecureHash) -> RetrievalLink:
        key = str(uuid.uuid4())
        self.memory[key] = secure_hash
        return RetrievalLink(key)

    def retrieve(self, link: RetrievalLink) -> SecureHash:
        if link not in self.memory:
            raise ValueError(f"{link=} not in hash-service")

        return SecureHash(self.memory[link])

    def verify(self, link: RetrievalLink, secure_hash: SecureHash) -> bool:
        return secure_hash == self.retrieve(link)

    def get_signing_provider_url(self) -> str | None:
        return self.signing_provider_url
