from datetime import datetime

from pydantic import BaseModel

from .normalizer import NormalizerMeta
from .raw_data import RawData


class RawDataReceivedEvent(BaseModel):
    created_at: datetime
    organization: str
    raw_data: RawData


class NormalizerMetaReceivedEvent(BaseModel):
    created_at: datetime
    organization: str
    normalizer_meta: NormalizerMeta
