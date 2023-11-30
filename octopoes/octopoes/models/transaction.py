from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel


class TransactionRecord(BaseModel):
    txTime: datetime
    txId: int
    validTime: datetime
    contentHash: str
    doc: Optional[Dict]
