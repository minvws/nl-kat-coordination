import datetime
from typing import List, Literal, Union

from pydantic import BaseModel


class Filter(BaseModel):
    field: str
    operator: Literal["eq", "ne", "lt", "le", "gt", "ge", "in_", "notin_"]
    value: Union[str, int, datetime.date]

    def get_field(self) -> List[str]:
        return self.field.split("__")
