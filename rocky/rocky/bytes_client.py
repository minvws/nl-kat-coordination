import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional

from django.conf import settings
import requests
from octopoes.api.models import Declaration

from rocky.health import ServiceHealth
from rocky.scheduler import BoefjeMeta, NormalizerMeta, Boefje, Normalizer

logger = logging.getLogger(__name__)


class BytesClient:
    def __init__(self, base_url: str, username: str, password: str, organization: str):
        self.base_url = base_url
        self.credentials = {
            "username": username,
            "password": password,
        }
        self.session = requests.session()
        self.organization = organization

    def health(self) -> ServiceHealth:
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()

        return ServiceHealth.parse_obj(response.json())

    @staticmethod
    def raw_from_declarations(declarations: List[Declaration]):
        json_string = f"[{','.join([declaration.json() for declaration in declarations])}]"

        return json_string.encode("utf-8")

    def add_manual_proof(self, normalizer_id: uuid.UUID, raw: bytes, manual_mime_types: Optional[Set[str]] = None):
        """Per convention for a generic normalizer, we add a raw list of declarations, not a single declaration"""

        if manual_mime_types is None:
            manual_mime_types = {"manual/ooi"}

        self.login()

        boefje_meta = BoefjeMeta(
            id=str(uuid.uuid4()),
            boefje=Boefje(id="manual"),
            input_ooi=None,
            arguments={},
            organization=self.organization,
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
        )

        self._save_boefje_meta(boefje_meta)
        raw_id = self._save_raw(boefje_meta.id, raw, {"manual", "boefje/manual"}.union(manual_mime_types))

        self._save_normalizer_meta(
            boefje_meta,
            NormalizerMeta(
                id=str(normalizer_id),
                raw_file_id=raw_id,
                normalizer=Normalizer(id="normalizer/manual"),
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
            ),
        )

    def upload_raw(self, raw: bytes, manual_mime_types: Set[str]):
        self.login()

        boefje_meta = BoefjeMeta(
            id=str(uuid.uuid4()),
            boefje=Boefje(id="manual"),
            input_ooi=None,
            arguments={},
            organization=self.organization,
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
        )

        self._save_boefje_meta(boefje_meta)
        self._save_raw(boefje_meta.id, raw, {"manual", "boefje/manual"}.union(manual_mime_types))

    def _save_boefje_meta(self, boefje_meta: BoefjeMeta) -> None:
        response = self.session.post(f"{self.base_url}/bytes/boefje_meta", data=boefje_meta.json())
        response.raise_for_status()

    def _save_normalizer_meta(self, boefje_meta: BoefjeMeta, normalizer_meta: NormalizerMeta) -> None:
        dehydrated_normalizer_meta = json.loads(normalizer_meta.json(exclude={"raw_data"}))
        dehydrated_normalizer_meta["boefje_meta"] = json.loads(boefje_meta.json())

        response = self.session.post(
            f"{self.base_url}/bytes/normalizer_meta", data=json.dumps(dehydrated_normalizer_meta)
        )

        response.raise_for_status()

    def _save_raw(self, boefje_meta_id: str, raw: bytes, mime_types: Set[str] = None) -> str:
        if not mime_types:
            mime_types = set()

        headers = {"content-type": "application/octet-stream"}
        headers.update(self.session.headers)

        response = self.session.post(
            f"{self.base_url}/bytes/raw/{boefje_meta_id}",
            raw,
            headers=headers,
            params={"mime_types": mime_types},
        )

        response.raise_for_status()
        return response.json()["id"]

    def get_raw(self, boefje_meta_id: str, raw_id: str) -> bytes:
        # Note: we assume organization permissions are handled before requesting raw data.

        response = self.session.get(f"{self.base_url}/bytes/raw/{boefje_meta_id}/{raw_id}")
        response.raise_for_status()

        return response.content

    def get_raw_metas(self, boefje_meta_id: str) -> List:
        # More than 100 raw files per Boefje run is very unlikely at this stage, but eventually we can start paginating
        raw_files_limit = 100
        params = {"boefje_meta_id": boefje_meta_id, "limit": raw_files_limit, "organization": self.organization}

        response = self.session.get(f"{self.base_url}/bytes/raw", params=params)
        response.raise_for_status()

        metas = response.json()

        if len(metas) >= raw_files_limit:
            logger.warning("Reached raw file limit for current view.")

        return metas

    def get_normalizer_meta(self, normalizer_meta_id: str) -> Dict:
        # Note: we assume organization permissions are handled before requesting raw data.

        response = self.session.get(f"{self.base_url}/bytes/normalizer_meta/{normalizer_meta_id}")
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


def get_bytes_client(organization: str) -> BytesClient:
    return BytesClient(settings.BYTES_API, settings.BYTES_USERNAME, settings.BYTES_PASSWORD, organization)
