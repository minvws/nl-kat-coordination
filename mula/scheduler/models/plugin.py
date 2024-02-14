import datetime

from pydantic import BaseModel


class Plugin(BaseModel):
    id: str
    type: str
    enabled: bool
    name: str | None = None
    version: str | None = None
    authors: list[str] | None = None
    created: datetime.datetime | None = None
    description: str | None = None
    environment_keys: list[str] | None = None
    related: list[str] | None = None
    scan_level: int | None = None
    consumes: str | list[str]
    options: list[str] | None = None
    produces: list[str]
