from typing import Literal

from pydantic import Field

from octopoes.models import OOI, Reference
from octopoes.models.ooi.web import HTTPHeader


class ContentSecurityPolicyHeader(OOI):
    ooi_type: Literal["Content-Security-Policy"] = "Content-Security-Policy"

    http_header: Reference = Field(ooi_type=HTTPHeader, max_inherit_scan_level=1)

