from pydantic import BaseModel, Field


class RawResponse(BaseModel):
    status: str
    message: str
    ids: list[str] | None = None


class File(BaseModel):
    name: str
    content: str = Field(json_schema_extra={"contentEncoding": "base64"})
    tags: list[str] = Field(default_factory=list)


class BoefjeOutput(BaseModel):
    files: list[File] = Field(default_factory=list)
