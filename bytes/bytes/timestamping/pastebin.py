import requests

from bytes.models import RetrievalLink, SecureHash
from bytes.repositories.hash_repository import HashRepository


class PastebinHashRepository(HashRepository):
    def __init__(self, api_dev_key: str):
        self.api_dev_key = api_dev_key
        self.session = requests.Session()
        self.url = "https://pastebin.com"

    def store(self, secure_hash: SecureHash) -> RetrievalLink:
        response = self.session.post(
            url=f"{self.url}/api/api_post.php",
            data={
                "api_paste_code": secure_hash,
                "api_option": "paste",
                "api_dev_key": self.api_dev_key,
                "api_paste_private": 1,  # Unlisted.
                "api_paste_expire_date": "N",  # Never
            },
        )

        if response.status_code != 200:
            raise ValueError(
                f"Couldn't save hash to pastebin,"
                f" {response.status_code=} content={response.content.decode('utf-8')}"
            )

        link = response.content.decode("utf-8")
        return RetrievalLink(link)

    def retrieve(self, link: RetrievalLink) -> SecureHash:
        if not link:
            raise ValueError("Can't retrieve secure-hash from empty link.")

        paste_id = link.split("/").pop()
        assert len(paste_id) > 0

        response = self.session.get(f"{self.url}/raw/{paste_id}")
        if response.status_code != 200:
            raise ValueError(
                f"Error retrieving pastebin data for {link=}, {response.status_code=},"
                f" content={response.content.decode('utf-8')}"
            )

        return SecureHash(response.content.decode())

    def verify(self, link: RetrievalLink, secure_hash: SecureHash) -> bool:
        return secure_hash == self.retrieve(link)

    def get_signing_provider_url(self) -> str | None:
        """Get the specific signing provider url"""

        return self.url
