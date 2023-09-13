import typing
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import UUID

import requests
from requests.exceptions import HTTPError

from bytes.models import BoefjeMeta, NormalizerMeta
from bytes.repositories.meta_repository import BoefjeMetaFilter, NormalizerMetaFilter, RawDataFilter

BYTES_API_CLIENT_VERSION = "0.2"


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
                raise

            self.login()
            return function(self, *args, **kwargs)

    return typing.cast(ClientSessionMethod, wrapper)


class BytesAPIClient:
    def __init__(self, base_url: str, username: str, password: str):
        self._session = BytesAPISession(base_url)
        self.credentials = {
            "username": username,
            "password": password,
        }
        self.headers: Dict[str, str] = {}

    def login(self) -> None:
        self.headers = self._get_authentication_headers()

    @staticmethod
    def _verify_response(response: requests.Response) -> None:
        response.raise_for_status()

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
    def get_metrics(self) -> bytes:
        response = self._session.get("/metrics", headers=self.headers)

        self._verify_response(response)

        return response.content

    @retry_with_login
    def save_boefje_meta(self, boefje_meta: BoefjeMeta) -> None:
        response = self._session.post("/bytes/boefje_meta", data=boefje_meta.json(), headers=self.headers)

        self._verify_response(response)

    @retry_with_login
    def get_boefje_meta_by_id(self, boefje_meta_id: UUID) -> BoefjeMeta:
        response = self._session.get(f"/bytes/boefje_meta/{boefje_meta_id}", headers=self.headers)
        self._verify_response(response)

        boefje_meta_json = response.json()
        return BoefjeMeta.parse_obj(boefje_meta_json)

    @retry_with_login
    def get_boefje_meta(self, query_filter: BoefjeMetaFilter) -> List[BoefjeMeta]:
        response = self._session.get("/bytes/boefje_meta", headers=self.headers, params=query_filter.dict())
        self._verify_response(response)

        boefje_meta_json = response.json()
        return [BoefjeMeta.parse_obj(boefje_meta) for boefje_meta in boefje_meta_json]

    @retry_with_login
    def save_normalizer_meta(self, normalizer_meta: NormalizerMeta) -> None:
        response = self._session.post("/bytes/normalizer_meta", data=normalizer_meta.json(), headers=self.headers)

        self._verify_response(response)

    @retry_with_login
    def get_normalizer_meta_by_id(self, normalizer_meta_id: UUID) -> NormalizerMeta:
        response = self._session.get(f"/bytes/normalizer_meta/{normalizer_meta_id}", headers=self.headers)
        self._verify_response(response)

        normalizer_meta_json = response.json()
        return NormalizerMeta.parse_obj(normalizer_meta_json)

    @retry_with_login
    def get_normalizer_meta(self, query_filter: NormalizerMetaFilter) -> List[NormalizerMeta]:
        response = self._session.get("/bytes/normalizer_meta", headers=self.headers, params=query_filter.dict())
        self._verify_response(response)

        normalizer_meta_json = response.json()
        return [NormalizerMeta.parse_obj(normalizer_meta) for normalizer_meta in normalizer_meta_json]

    @retry_with_login
    def save_raw(self, boefje_meta_id: UUID, raw: bytes, mime_types: Optional[List[str]] = None) -> str:
        if not mime_types:
            mime_types = []

        headers = {"content-type": "application/octet-stream"}
        headers.update(self.headers)

        response = self._session.post(
            "/bytes/raw", raw, headers=headers, params={"mime_types": mime_types, "boefje_meta_id": str(boefje_meta_id)}
        )

        self._verify_response(response)
        raw_id = response.json()["id"]

        return str(raw_id)

    @retry_with_login
    def get_raw(self, raw_id: UUID) -> bytes:
        response = self._session.get(f"/bytes/raw/{raw_id}", headers=self.headers, stream=True)
        self._verify_response(response)

        return response.content

    @retry_with_login
    def get_raws(self, query_filter: RawDataFilter) -> Dict[str, str]:
        params = query_filter.dict()
        params["mime_types"] = [m.value for m in query_filter.mime_types]

        response = self._session.get("/bytes/raw", headers=self.headers, stream=True, params=params)
        self._verify_response(response)

        return response.json()  # type: ignore
