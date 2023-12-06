from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class TransactionRecord(BaseModel):
    transaction_time: datetime = Field(alias="txTime")
    transaction_id: int = Field(alias="txId")
    valid_time: datetime = Field(alias="validTime")
    content_hash: str = Field(alias="contentHash")
    document: Optional[Dict] = Field(None, alias="doc")
