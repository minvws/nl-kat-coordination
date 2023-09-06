from datetime import datetime

from pydantic import BaseModel

from .raw_data import RawData


class RawDataReceivedEvent(BaseModel):
    created_at: datetime
    organization: str
    raw_data: RawData
