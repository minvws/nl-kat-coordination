from pathlib import Path
from typing import Literal

from pydantic import BaseModel

KATALOGUS_DIR = Path(__file__).parent
STATIC_DIR = KATALOGUS_DIR / "static"

LIMIT = 100


class PaginationParameters(BaseModel):
    offset: int = 0
    limit: int = LIMIT


class FilterParameters(BaseModel):
    q: str | None = None
    type: Literal["boefje", "normalizer", "bit"] | None = None
    state: bool | None = None
    scan_level: int = 0
