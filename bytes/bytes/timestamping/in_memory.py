import uuid
from typing import Dict

from bytes.models import RetrievalLink, SecureHash
from bytes.repositories.hash_repository import HashRepository


class InMemoryHashRepository(HashRepository):
    def __init__(self) -> None:
        self.memory: Dict[str, SecureHash] = {}

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
