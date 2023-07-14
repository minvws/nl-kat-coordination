from pathlib import Path
from typing import Literal, Optional, Union

from pydantic import BaseModel

KATALOGUS_DIR = Path(__file__).parent
STATIC_DIR = KATALOGUS_DIR / "static"

LIMIT = 100


class PaginationParameters(BaseModel):
    offset: int = 0
    limit: Optional[int] = LIMIT


class FilterParameters(BaseModel):
    q: Optional[str] = None
    type: Optional[Union[Literal["boefje"], Literal["normalizer"], Literal["bit"]]] = None
    state: Optional[bool] = None
    scan_level: int = 0
