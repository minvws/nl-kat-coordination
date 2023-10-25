from datetime import datetime

from pydantic.v1.datetime_parse import parse_datetime


def _validate_timezone_aware_datetime(value: datetime) -> datetime:
    parsed = parse_datetime(value)
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise ValueError(f"{parsed} is not timezone aware")
    return parsed
