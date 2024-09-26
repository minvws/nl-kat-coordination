from __future__ import annotations

from pydantic import Field
from pydantic.fields import FieldInfo

from octopoes.models import OOI


def ReferenceField(
    object_type: str | type[OOI],
    *,
    max_issue_scan_level: int | None = None,
    max_inherit_scan_level: int | None = None,
    **kwargs,
) -> FieldInfo:
    if not isinstance(object_type, str):
        object_type = object_type.get_object_type()

    json_schema_extra = {
        "object_type": object_type,
        "max_issue_scan_level": max_issue_scan_level,
        "max_inherit_scan_level": max_inherit_scan_level,
    }

    return Field(**kwargs, json_schema_extra=json_schema_extra)
