import typing
from collections.abc import Callable
from functools import wraps
from typing import Any
from uuid import UUID

import httpx
from httpx import HTTPError

from bytes.models import BoefjeMeta, NormalizerMeta
from bytes.repositories.meta_repository import BoefjeMetaFilter, NormalizerMetaFilter, RawDataFilter

BYTES_API_CLIENT_VERSION = "0.2"

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
        self.client = httpx.Client(
            base_url=base_url, headers={"User-Agent": f"bytes-api-client/{BYTES_API_CLIENT_VERSION}"}
        )
        self._credentials = {
            "username": username,
            "password": password,
        }

    def login(self) -> None:
        self.client.headers.update(self._get_authentication_headers())

    @staticmethod
    def _verify_response(response: httpx.Response) -> None:
        response.raise_for_status()

    def _get_authentication_headers(self) -> dict[str, str]:
        return {"Authorization": f"bearer {self._get_token()}"}

    def _get_token(self) -> str:
        response = self.client.post(
            "/token",
            data=self._credentials,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

        return str(response.json()["access_token"])

    @retry_with_login
    def get_metrics(self) -> bytes:
        response = self.client.get("/metrics")

        self._verify_response(response)

        return response.content

    @retry_with_login
    def get_mime_type_count(self, query_filter: RawDataFilter) -> dict[str, str]:
        params = query_filter.model_dump(exclude_none=True)
        params["mime_types"] = [m.value for m in query_filter.mime_types]

        response = self.client.get("/bytes/mime_types", params=params)
        self._verify_response(response)

        return response.json()  # type: ignore

    @retry_with_login
    def save_boefje_meta(self, boefje_meta: BoefjeMeta) -> None:
        response = self.client.post("/bytes/boefje_meta", content=boefje_meta.model_dump_json())

        self._verify_response(response)

    @retry_with_login
    def get_boefje_meta_by_id(self, boefje_meta_id: UUID) -> BoefjeMeta:
        response = self.client.get(f"/bytes/boefje_meta/{boefje_meta_id}")
        self._verify_response(response)

        boefje_meta_json = response.json()
        return BoefjeMeta.parse_obj(boefje_meta_json)

    @retry_with_login
    def get_boefje_meta(self, query_filter: BoefjeMetaFilter) -> list[BoefjeMeta]:
        response = self.client.get("/bytes/boefje_meta", params=query_filter.model_dump(exclude_none=True))
        self._verify_response(response)

        boefje_meta_json = response.json()
        return [BoefjeMeta.parse_obj(boefje_meta) for boefje_meta in boefje_meta_json]

    @retry_with_login
    def save_normalizer_meta(self, normalizer_meta: NormalizerMeta) -> None:
        response = self.client.post("/bytes/normalizer_meta", content=normalizer_meta.model_dump_json())

        self._verify_response(response)

    @retry_with_login
    def get_normalizer_meta_by_id(self, normalizer_meta_id: UUID) -> NormalizerMeta:
        response = self.client.get(f"/bytes/normalizer_meta/{normalizer_meta_id}")
        self._verify_response(response)

        normalizer_meta_json = response.json()
        return NormalizerMeta.parse_obj(normalizer_meta_json)

    @retry_with_login
    def get_normalizer_meta(self, query_filter: NormalizerMetaFilter) -> list[NormalizerMeta]:
        response = self.client.get("/bytes/normalizer_meta", params=query_filter.model_dump(exclude_none=True))
        self._verify_response(response)

        normalizer_meta_json = response.json()
        return [NormalizerMeta.parse_obj(normalizer_meta) for normalizer_meta in normalizer_meta_json]

    @retry_with_login
    def save_raw(self, boefje_meta_id: UUID, raw: bytes, mime_types: list[str] | None = None) -> str:
        if not mime_types:
            mime_types = []

        content_type = ",".join(mime_types)
        response = self.client.post(
            "/bytes/raw",
            files=[("raws", ("raws", raw, content_type))],
            params={"boefje_meta_id": str(boefje_meta_id)},
        )
        self._verify_response(response)

        return response.json()[content_type]

    @retry_with_login
    def get_raw(self, raw_id: UUID) -> bytes:
        response = self.client.get(f"/bytes/raw/{raw_id}")
        self._verify_response(response)

        return response.content

    @retry_with_login
    def get_raws(self, query_filter: RawDataFilter) -> dict[str, str]:
        params = query_filter.model_dump(exclude_none=True)
        params["mime_types"] = [m.value for m in query_filter.mime_types]

        response = self.client.get("/bytes/raw", params=params)
        self._verify_response(response)

        return response.json()  # type: ignore
