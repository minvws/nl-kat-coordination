from pydantic import BaseModel


class RawResponse(BaseModel):
    status: str
    message: str
    ids: list[str] | None = None
