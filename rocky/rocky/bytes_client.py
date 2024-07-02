import uuid
from collections.abc import Set
from datetime import datetime, timezone

import httpx
import structlog
from django.conf import settings
from django.http import Http404

from octopoes.api.models import Declaration
from rocky.health import ServiceHealth
from rocky.scheduler import Boefje, BoefjeMeta, Normalizer, NormalizerMeta, RawData

logger = structlog.get_logger(__name__)


class BytesClient:
    def __init__(self, base_url: str, username: str, password: str, organization: str):
        self.credentials = {
            "username": username,
            "password": password,
        }
        self.session = httpx.Client(base_url=base_url)
        self.organization = organization

    def health(self) -> ServiceHealth:
        response = self.session.get("/health")
        response.raise_for_status()

        return ServiceHealth.parse_obj(response.json())

    @staticmethod
    def raw_from_declarations(declarations: list[Declaration]):
        json_string = f"[{','.join([declaration.json() for declaration in declarations])}]"

        return json_string.encode("utf-8")

    def add_manual_proof(
        self, normalizer_id: uuid.UUID, raw: bytes, manual_mime_types: Set[str] = frozenset({"manual/ooi"})
    ):
        """Per convention for a generic normalizer, we add a raw list of declarations, not a single declaration"""

        self.login()

        boefje_meta = BoefjeMeta(
            id=uuid.uuid4(),
            boefje=Boefje(id="manual"),
            input_ooi=None,
            arguments={},
            organization=self.organization,
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
        )

        self._save_boefje_meta(boefje_meta)
        all_mime_types = {"boefje/manual"}.union(manual_mime_types)
        raw_id = self._save_raw(boefje_meta.id, raw, all_mime_types)

        self._save_normalizer_meta(
            NormalizerMeta(
                id=normalizer_id,
                raw_data=RawData(
                    id=uuid.UUID(raw_id),
                    boefje_meta=boefje_meta,
                    mime_types=[{"value": mime_type} for mime_type in all_mime_types],
                ),
                normalizer=Normalizer(id="normalizer/manual"),
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
            ),
        )

    def upload_raw(self, raw: bytes, manual_mime_types: set[str], input_ooi: str | None = None) -> str:
        self.login()

        boefje_meta = BoefjeMeta(
            id=uuid.uuid4(),
            boefje=Boefje(id="manual"),
            input_ooi=input_ooi,
            arguments={},
            organization=self.organization,
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
        )

        self._save_boefje_meta(boefje_meta)
        raw_id = self._save_raw(boefje_meta.id, raw, {"boefje/manual"}.union(manual_mime_types))
        return raw_id

    def _save_boefje_meta(self, boefje_meta: BoefjeMeta) -> None:
        response = self.session.post(
            "/bytes/boefje_meta", content=boefje_meta.model_dump_json(), headers={"content-type": "application/json"}
        )
        response.raise_for_status()

    def _save_normalizer_meta(self, normalizer_meta: NormalizerMeta) -> None:
        response = self.session.post(
            "/bytes/normalizer_meta",
            content=normalizer_meta.model_dump_json(),
            headers={"content-type": "application/json"},
        )

        response.raise_for_status()

    def _save_raw(self, boefje_meta_id: uuid.UUID, raw: bytes, mime_types: Set[str] = frozenset()) -> str:
        response = self.session.post(
            "/bytes/raw",
            content=raw,
            headers={"content-type": "application/octet-stream"},
            params={"mime_types": list(mime_types), "boefje_meta_id": str(boefje_meta_id)},
        )

        response.raise_for_status()
        return response.json()["id"]

    def get_raw(self, raw_id: str) -> bytes:
        # Note: we assume organization permissions are handled before requesting raw data.

        response = self.session.get(f"/bytes/raw/{raw_id}")
        response.raise_for_status()

        return response.content

    def get_raw_metas(self, boefje_meta_id: uuid.UUID, organization_code: str) -> list:
        # More than 100 raw files per Boefje run is very unlikely at this stage, but eventually we can start paginating
        raw_files_limit = 100
        params: dict[str, str | int] = {
            "boefje_meta_id": str(boefje_meta_id),
            "limit": raw_files_limit,
            "organization": str(self.organization),
        }

        response = self.session.get("/bytes/raw", params=params)
        response.raise_for_status()

        metas = response.json()
        metas = [raw_meta for raw_meta in metas if raw_meta["boefje_meta"]["organization"] == organization_code]
        if not metas:
            raise Http404
        if len(metas) >= raw_files_limit:
            logger.warning("Reached raw file limit for current view.")

        return metas

    def get_normalizer_meta(self, normalizer_meta_id: uuid.UUID) -> dict:
        # Note: we assume organization permissions are handled before requesting raw data.

        response = self.session.get(f"/bytes/normalizer_meta/{normalizer_meta_id}")
        response.raise_for_status()

        return response.json()

    def login(self):
        self.session.headers.update(self._authorization_header())

    def _authorization_header(self) -> dict[str, str]:
        return {"Authorization": f"bearer {self._get_token()}"}

    def _get_token(self) -> str:
        response = self.session.post(
            "/token",
            data=self.credentials,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

        return response.json()["access_token"]


def get_bytes_client(organization: str) -> BytesClient:
    return BytesClient(settings.BYTES_API, settings.BYTES_USERNAME, settings.BYTES_PASSWORD, organization)
