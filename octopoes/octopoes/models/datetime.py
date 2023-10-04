from datetime import datetime

from pydantic.datetime_parse import parse_datetime


class TimezoneAwareDatetime(datetime):
    @classmethod
    # TODO[pydantic]: We couldn't refactor `__get_validators__`, please create the `__get_pydantic_core_schema__` manually.
    # Check https://docs.pydantic.dev/latest/migration/#defining-custom-types for more information.
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        v = parse_datetime(v)
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError(f"{v} is not timezone aware")
        return v
