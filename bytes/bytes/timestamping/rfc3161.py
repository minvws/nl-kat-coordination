import base64

import rfc3161ng

from bytes.models import SecureHash, RetrievalLink
from bytes.repositories.hash_repository import HashRepository


class RFC3161HashRepository(HashRepository):
    """A service that uses an external Trusted Timestamp Authority (TSA) that complies with RFC3161."""

    def __init__(self, certificate: bytes, url: str):
        self.timestamper = rfc3161ng.RemoteTimestamper(url=url, certificate=certificate)

    def store(self, secure_hash: SecureHash) -> RetrievalLink:
        time_stamp_token: bytes = self.timestamper.timestamp(data=secure_hash.encode())
        encoded = base64.b64encode(time_stamp_token).decode()

        return RetrievalLink(encoded)

    def verify(self, link: RetrievalLink, secure_hash: SecureHash) -> bool:
        # Note: "link" is an inconvenient name for this implementation since it is a token.

        if link == "":
            raise ValueError("Can't retrieve secure-hash from empty link.")

        time_stamp_token = base64.b64decode(str(link))

        assert rfc3161ng.get_timestamp(time_stamp_token)

        return self.timestamper.check(time_stamp_token, data=secure_hash.encode())  # type: ignore
