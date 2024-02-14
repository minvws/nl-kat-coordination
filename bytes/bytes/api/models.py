from pydantic import BaseModel


class RawResponse(BaseModel):
    status: str
    message: str
    id: str | None = None
