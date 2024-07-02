from pydantic import BaseModel, ConfigDict, Field


class Schedule(BaseModel):
    model_config = ConfigDict(from_attributes=True)
