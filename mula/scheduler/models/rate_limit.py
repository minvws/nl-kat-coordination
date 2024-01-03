from pydantic import BaseModel, constr


class RateLimit(BaseModel):
    interval: str
    identifier: str = constr(min_length=1)
