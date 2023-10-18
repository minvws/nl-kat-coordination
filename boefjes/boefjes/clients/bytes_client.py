import logging
import typing
from functools import wraps
from typing import Any, Callable, Dict, Set, Union
from uuid import UUID

import requests
from requests.adapters import HTTPAdapter
from requests.models import HTTPError

from boefjes.clients.scheduler_client import LogRetry
from boefjes.job_models import BoefjeMeta, NormalizerMeta, RawDataMeta

BYTES_API_CLIENT_VERSION = "0.3"
logger = logging.getLogger(__name__)


class BytesAPISession(requests.Session):
    def __init__(self, base_url: str):
        super().__init__()

        self._base_url = base_url
        self.headers["User-Agent"] = f"bytes-api-client/{BYTES_API_CLIENT_VERSION}"

    def request(self, method: str, url: Union[str, bytes], **kwargs) -> requests.Response:  # type: ignore
        url = self._base_url + str(url)

        return super().request(method, url, **kwargs)


ClientSessionMethod = Callable[..., Any]


def retry_with_login(function: ClientSessionMethod) -> ClientSessionMethod:
    @wraps(function)
    def wrapper(self, *args, **kwargs):  # type: ignore
        try:
            return function(self, *args, **kwargs)
        except HTTPError as error:
            if error.response.status_code != 401:
                raise error from HTTPError

            self.login()
            return function(self, *args, **kwargs)

    return typing.cast(ClientSessionMethod, wrapper)


class BytesAPIClient:
    def __init__(self, base_url: str, username: str, password: str):
        self._session = BytesAPISession(base_url)

        max_retries = LogRetry(total=6, backoff_factor=1, skip_log=True)
        self._session.mount("https://", HTTPAdapter(max_retries=max_retries))
        self._session.mount("http://", HTTPAdapter(max_retries=max_retries))

        self.credentials = {
            "username": username,
            "password": password,
        }
        self.headers: Dict[str, str] = {}

    def login(self) -> None:
        self.headers = self._get_authentication_headers()

    @staticmethod
    def _verify_response(response: requests.Response) -> None:
        try:
            response.raise_for_status()
        except HTTPError:
            logger.error(response.text)
            raise

    def _get_authentication_headers(self) -> Dict[str, str]:
        return {"Authorization": f"bearer {self._get_token()}"}

    def _get_token(self) -> str:
        response = self._session.post(
            "/token",
            data=self.credentials,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

        return str(response.json()["access_token"])

    @retry_with_login
    def save_boefje_meta(self, boefje_meta: BoefjeMeta) -> None:
        response = self._session.post("/bytes/boefje_meta", data=boefje_meta.json(), headers=self.headers)

        self._verify_response(response)

    @retry_with_login
    def get_boefje_meta(self, boefje_meta_id: str) -> BoefjeMeta:
        response = self._session.get(f"/bytes/boefje_meta/{boefje_meta_id}", headers=self.headers)
        self._verify_response(response)

        boefje_meta_json = response.json()
        return BoefjeMeta.parse_obj(boefje_meta_json)

    @retry_with_login
    def save_normalizer_meta(self, normalizer_meta: NormalizerMeta) -> None:
        response = self._session.post("/bytes/normalizer_meta", data=normalizer_meta.json(), headers=self.headers)

        self._verify_response(response)

    @retry_with_login
    def save_raw(self, boefje_meta_id: str, raw: bytes, mime_types: Set[str] = frozenset()) -> UUID:
        headers = {"content-type": "application/octet-stream"}
        headers.update(self.headers)

        response = self._session.post(
            "/bytes/raw",
            raw,
            headers=headers,
            params={"mime_types": mime_types, "boefje_meta_id": boefje_meta_id},
        )

        self._verify_response(response)

        return UUID(response.json()["id"])

    @retry_with_login
    def get_raw(self, raw_data_id: str) -> bytes:
        response = self._session.get(f"/bytes/raw/{raw_data_id}", headers=self.headers)
        self._verify_response(response)

        return response.content

    @retry_with_login
    def get_raw_meta(self, raw_data_id: str) -> RawDataMeta:
        response = self._session.get(f"/bytes/raw/{raw_data_id}/meta", headers=self.headers)
        self._verify_response(response)

        return RawDataMeta.parse_obj(response.json())
