import uuid

from pydantic import BaseModel

from .boefje import BoefjeMeta


class RawData(BaseModel):
    id: uuid.UUID
    boefje_meta: BoefjeMeta
    mime_types: list[dict[str, str]]
    secure_hash: str | None
    hash_retrieval_link: str | None
