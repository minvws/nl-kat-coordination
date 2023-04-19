import json
from json import JSONDecodeError
from typing import Literal

from jsonschema.exceptions import SchemaError
from jsonschema.validators import Draft202012Validator
from pydantic.class_validators import validator

from octopoes.models import OOI, Reference
from octopoes.models.persistence import ReferenceField


class Question(OOI):
    object_type: Literal["Question"] = "Question"

    ooi: Reference = ReferenceField(OOI)
    schema_id: str
    json_schema: str

    _natural_key_attrs = ["schema_id", "ooi"]
    _traversable = False

    @validator("json_schema")
    def json_schema_valid(cls, schema: str) -> str:
        try:
            val = Draft202012Validator({})
            val.check_schema(json.loads(schema))
        except JSONDecodeError as e:
            raise ValueError("The json_schema is not valid JSON") from e
        except SchemaError as e:
            raise ValueError("The json_schema field is not a valid JSON schema") from e

        return schema
