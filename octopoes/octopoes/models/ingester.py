"""Representation of a ingesters.Ingester instance. Used by HTTP Server."""
from typing import Optional

from pydantic import BaseModel


class Ingester(BaseModel):
    """Representation of a ingesters.Ingester instance."""

    id: Optional[str]
