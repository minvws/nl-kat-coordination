from datetime import datetime

from pydantic import AfterValidator
from pydantic.v1.datetime_parse import parse_datetime
from typing_extensions import Annotated


def _validate_timezone_aware_datetime(value: datetime) -> datetime:
    parsed = parse_datetime(value)
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise ValueError(f"{parsed} is not timezone aware")
    return parsed


TimezoneAwareDatetime = Annotated[datetime, AfterValidator(_validate_timezone_aware_datetime)]
