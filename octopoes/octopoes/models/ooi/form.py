import json
from json import JSONDecodeError
from typing import Literal, Optional

from jsonschema.exceptions import SchemaError, ValidationError
from jsonschema.validators import Draft202012Validator, validate as schema_validate
from pydantic.class_validators import validator

from octopoes.models import OOI, Reference
from octopoes.models.persistence import ReferenceField


class FormQuestionAnswer(OOI):
    object_type: Literal["FormQuestionAnswer"] = "FormQuestionAnswer"

    reason: Reference = ReferenceField(OOI)
    json_schema: str
    answer: Optional[str]

    @validator("answer")
    def value_conforming_schema(cls, answer: Optional[str], values) -> Optional[str]:
        if answer is None:
            return answer

        try:
            schema_validate(json.loads(answer), json.loads(values["json_schema"]))
        except JSONDecodeError as e:
            raise ValueError("The answer field is not valid JSON") from e
        except ValidationError as e:
            raise ValueError("The answer does not conform to the JSON schema") from e

        return answer

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

