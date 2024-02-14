from bytes.models import RetrievalLink, SecureHash


class HashRepository:
    """Save a hash of the data and verify that we have seen the hash through an external party"""

    def store(self, secure_hash: SecureHash) -> RetrievalLink:
        """Send the hash to the external party"""

        raise NotImplementedError()

    def verify(self, link: RetrievalLink, secure_hash: SecureHash) -> bool:
        """Verify that the external party has seen the hash"""

        raise NotImplementedError()

    def get_signing_provider_url(self) -> str | None:
        """Get the specific signing provider url"""

        raise NotImplementedError()
