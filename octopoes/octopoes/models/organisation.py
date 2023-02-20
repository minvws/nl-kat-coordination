"""Organisation model."""
from pydantic import BaseModel


class Organisation(BaseModel):
    """Organisation model."""

    id: str
    name: str
