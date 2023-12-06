from typing import Optional

from pydantic import BaseModel


class RawResponse(BaseModel):
    status: str
    message: str
    id: Optional[str] = None
