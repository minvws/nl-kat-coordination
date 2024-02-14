"""
DNS Report Datamodel
"""

from pydantic import BaseModel

from keiko.base_models import DataShapeBase


class DNSRecord(BaseModel):
    primary_key: str
    network: str
    hostname: str
    dns_record_type: str
    ttl: int
    value: str


class Hostname(BaseModel):
    primary_key: str
    name: str
    network: str
    dns_records: list[DNSRecord]


class DataShape(DataShapeBase):
    hostnames: list[Hostname]
