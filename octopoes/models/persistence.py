from __future__ import annotations

from typing import Union, Type, Optional

from pydantic import Field
from pydantic.fields import FieldInfo

from octopoes.models import OOI


def ReferenceField(
    object_type: Union[str, Type[OOI]],
    *,
    max_issue_scan_level: Optional[int] = None,
    max_inherit_scan_level: Optional[int] = None,
    **kwargs,
) -> FieldInfo:
    kwargs.update(
        {
            "object_type": object_type,
            "max_issue_scan_level": max_issue_scan_level,
            "max_inherit_scan_level": max_inherit_scan_level,
        }
    )
    return Field(**kwargs)
