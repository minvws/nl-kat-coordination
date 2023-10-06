from datetime import datetime

from pydantic import AfterValidator
from pydantic.v1.datetime_parse import parse_datetime
from typing_extensions import Annotated

# class TimezoneAwareDatetime(datetime):
#     @classmethod
#     # TODO[pydantic]: We couldn't refactor `__get_validators__`, please create the `__get_pydantic_core_schema__` manually.
#     # Check https://docs.pydantic.dev/latest/migration/#defining-custom-types for more information.
#     def __get_validators__(cls):
#         yield cls.validate
#
#     @classmethod
#     def validate(cls, v):
#         if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:


def _validate_timezone_aware_datetime(value: datetime) -> datetime:
    parsed = parse_datetime(value)
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise ValueError(f"{parsed} is not timezone aware")
    return parsed


TimezoneAwareDatetime = Annotated[datetime, AfterValidator(_validate_timezone_aware_datetime)]
