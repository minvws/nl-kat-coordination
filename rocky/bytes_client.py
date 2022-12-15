import logging
from typing import Dict, List

import requests

from rocky.health import ServiceHealth
from rocky.settings import BYTES_API, BYTES_USERNAME, BYTES_PASSWORD


logger = logging.getLogger(__name__)


class BytesClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.credentials = {
            "username": username,
            "password": password,
        }
        self.session = requests.session()

    def health(self) -> ServiceHealth:
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()

        return ServiceHealth.parse_obj(response.json())

    def get_raw(self, boefje_meta_id: str, raw_id: str) -> bytes:
        response = self.session.get(f"{self.base_url}/bytes/raw/{boefje_meta_id}/{raw_id}")
        response.raise_for_status()

        return response.content

    def get_raw_metas(self, boefje_meta_id: str) -> List:
        # More than 100 raw files per Boefje run is very unlikely at this stage, but eventually we can start paginating
        raw_files_limit = 100
        params = {"boefje_meta_id": boefje_meta_id, "limit": raw_files_limit}

        response = self.session.get(f"{self.base_url}/bytes/raw", params=params)
        response.raise_for_status()

        metas = response.json()

        if len(metas) >= raw_files_limit:
            logger.warning("Reached raw file limit for current view.")

        return metas

    def get_raw_meta(self, boefje_meta_id: str):
        response = self.session.get(
            f"{self.base_url}/bytes/raw?boefje_meta_id={boefje_meta_id}&limit=1",
        )
        response.raise_for_status()

        return response.json()

    def get_normalizer_meta(self, normalizer_meta_id: str) -> Dict:
        response = self.session.get(
            f"{self.base_url}/bytes/normalizer_meta/{normalizer_meta_id}",
        )
        response.raise_for_status()

        return response.json()

    def login(self):
        self.session.headers.update(self._authorization_header())

    def _authorization_header(self) -> Dict[str, str]:
        return {"Authorization": f"bearer {self._get_token()}"}

    def _get_token(self) -> str:
        response = self.session.post(
            f"{self.base_url}/token",
            data=self.credentials,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

        return response.json()["access_token"]


def get_bytes_client() -> BytesClient:
    return BytesClient(BYTES_API, BYTES_USERNAME, BYTES_PASSWORD)
