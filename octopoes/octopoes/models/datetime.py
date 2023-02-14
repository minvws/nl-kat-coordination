from datetime import datetime

from pydantic.datetime_parse import parse_datetime


class TimezoneAwareDatetime(datetime):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        v = parse_datetime(v)
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError(f"{v} is not timezone aware")
        return v
