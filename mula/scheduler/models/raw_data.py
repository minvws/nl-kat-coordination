import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel

from .boefje import BoefjeMeta


class RawData(BaseModel):
    id: uuid.UUID
    boefje_meta: BoefjeMeta
    mime_types: List[Dict[str, str]]
    secure_hash: Optional[str]
    hash_retrieval_link: Optional[str]
