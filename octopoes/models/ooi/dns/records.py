import abc
import hashlib
from typing import Optional, Literal, List

from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, IPAddress, NetBlock
from octopoes.models.persistence import ReferenceField


class DNSRecord(OOI, abc.ABC):
    hostname: Reference = ReferenceField(Hostname, max_issue_scan_level=0, max_inherit_scan_level=2)
    dns_record_type: Literal["A", "AAAA", "CNAME", "MX", "NS", "PTR", "SOA", "SRV", "TXT"]
    value: str
    ttl: Optional[int]  # todo: validation

    _natural_key_attrs = ["hostname", "value"]
    _reverse_relation_names = {
        "hostname": "dns_records",
    }

    @classmethod
    def _get_record_type(cls) -> str:
        end_index = cls.__name__.index("Record")
        return cls.__name__[3:end_index]

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        dns_record_type = cls._get_record_type()
        return f"{reference.tokenized.hostname.name} {dns_record_type} {reference.tokenized.value}"


class DNSARecord(DNSRecord):
    object_type: Literal["DNSARecord"] = "DNSARecord"
    dns_record_type: Literal["A"] = "A"

    address: Reference = ReferenceField(IPAddressV4)

    _reverse_relation_names = {"hostname": "dns_a_records", "address": "dns_a_records"}


class DNSAAAARecord(DNSRecord):
    object_type: Literal["DNSAAAARecord"] = "DNSAAAARecord"
    dns_record_type: Literal["AAAA"] = "AAAA"

    address: Reference = ReferenceField(IPAddressV6)

    _reverse_relation_names = {
        "hostname": "dns_aaaa_records",
        "address": "dns_aaaa_records",
    }


class DNSMXRecord(DNSRecord):
    object_type: Literal["DNSMXRecord"] = "DNSMXRecord"
    dns_record_type: Literal["MX"] = "MX"

    mail_hostname: Optional[Reference] = ReferenceField(Hostname, default=None)
    preference: Optional[int]

    _reverse_relation_names = {
        "hostname": "dns_mx_records",
        "mail_hostname": "mail_server_of",
    }


class DNSTXTRecord(DNSRecord):
    object_type: Literal["DNSTXTRecord"] = "DNSTXTRecord"
    dns_record_type: Literal["TXT"] = "TXT"

    @property
    def natural_key(self) -> str:
        sha = hashlib.sha1(self.value.encode("UTF-8")).hexdigest()
        key = super().natural_key
        return key.replace(self.value, sha)

    _reverse_relation_names = {"hostname": "dns_txt_records"}


class DNSNSRecord(DNSRecord):
    object_type: Literal["DNSNSRecord"] = "DNSNSRecord"
    dns_record_type: Literal["NS"] = "NS"

    name_server_hostname: Reference = ReferenceField(Hostname, max_issue_scan_level=2, max_inherit_scan_level=0)

    _reverse_relation_names = {
        "hostname": "dns_ns_records",
        "name_server_hostname": "ns_record_targets",
    }


class DNSCNAMERecord(DNSRecord):
    object_type: Literal["DNSCNAMERecord"] = "DNSCNAMERecord"
    dns_record_type: Literal["CNAME"] = "CNAME"

    target_hostname: Reference = ReferenceField(Hostname)

    _reverse_relation_names = {
        "hostname": "dns_cname_records",
        "target_hostname": "cname_target_of",
    }


class DNSSOARecord(DNSRecord):
    object_type: Literal["DNSSOARecord"] = "DNSSOARecord"
    dns_record_type: Literal["SOA"] = "SOA"

    soa_hostname: Reference = ReferenceField(Hostname)
    serial: Optional[int]
    retry: Optional[int]
    refresh: Optional[int]
    expire: Optional[int]
    minimum: Optional[int]

    _reverse_relation_names = {
        "hostname": "dns_soa_records",
        "soa_hostname": "subject_of_dns_soa_records",
    }

    _natural_key_attrs = ["hostname", "soa_hostname"]

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        dns_record_type = cls._get_record_type()
        return f"{reference.tokenized.hostname.name} {dns_record_type} {reference.tokenized.soa_hostname.name}"


class DNSSPFRecord(OOI):
    object_type: Literal["DNSSPFRecord"] = "DNSSPFRecord"
    value: str
    ttl: Optional[int]
    all: Optional[str]
    ptr: Optional[str]
    dns_txt_record: Reference = ReferenceField(DNSTXTRecord)

    include: Optional[List[Reference]] = ReferenceField(Hostname, default=None)
    redirect: Optional[List[Reference]] = ReferenceField(Hostname, default=None)

    _natural_key_attrs = ["dns_txt_record", "value"]
    _reverse_relation_names = {
        "dns_txt_record": "dns_spf_record",
    }

    @property
    def natural_key(self) -> str:
        sha = hashlib.sha1(self.value.encode("UTF-8")).hexdigest()
        key = super().natural_key
        return key.replace(self.value, sha)

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"SPF Record of {reference.tokenized.dns_txt_record.mock_hostname.name}"


class DNSSPFMechanism(OOI):
    spf_record: Reference = ReferenceField(DNSSPFRecord)
    qualifier: str
    mechanism: str


class DNSSPFMechanismIP(DNSSPFMechanism):
    object_type: Literal["DNSSPFMechanismIP"] = "DNSSPFMechanismIP"

    ip: Reference = ReferenceField(IPAddress)

    _natural_key_attrs = ["spf_record", "qualifier", "mechanism", "ip"]
    _information_value = ["qualifier"]
    _reverse_relation_names = {
        "spf_record": "spf_ip_mechanisms",
    }

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"SPF Record of {reference.tokenized.spf_record.dns_txt_record.mock_hostname.name} to {reference.tokenized.qualifier} {reference.tokenized.ip.address}"


class DNSSPFMechanismHostname(DNSSPFMechanism):
    object_type: Literal["DNSSPFMechanismHostname"] = "DNSSPFMechanismHostname"

    hostname: Reference = ReferenceField(Hostname)

    _natural_key_attrs = ["spf_record", "qualifier", "mechanism", "hostname"]
    _information_value = ["qualifier"]
    _reverse_relation_names = {
        "spf_record": "spf_hostname_mechanisms",
    }

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"SPF Record of {reference.tokenized.spf_record.dns_txt_record.mock_hostname.name} to {reference.tokenized.qualifier} {reference.tokenized.hostname.name}"


class DNSSPFMechanismNetBlock(DNSSPFMechanism):
    object_type: Literal["DNSSPFMechanismNetBlock"] = "DNSSPFMechanismNetBlock"

    netblock: Reference = ReferenceField(NetBlock)

    _natural_key_attrs = ["spf_record", "qualifier", "mechanism", "netblock"]
    _information_value = ["qualifier"]
    _reverse_relation_names = {
        "spf_record": "spf_netblock_mechanisms",
    }

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"SPF Record of {reference.tokenized.spf_record.dns_txt_record.mock_hostname.name} to {reference.tokenized.qualifier} {reference.tokenized.netblock.start_ip}/{reference.tokenized.netblock.mask}"


class NXDOMAIN(OOI):
    object_type: Literal["NXDOMAIN"] = "NXDOMAIN"

    hostname: Reference = ReferenceField(Hostname)

    _natural_key_attrs = ["hostname"]
    _reverse_relation_names = {
        "hostname": "nxdomain_hostname",
    }

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"NXDOMAIN response on {reference.tokenized.hostname.name}"


# class DNSNTA7516Record(DNSRecord):
#     expiry: Optional[datetime]

# class DNSDKIMRecord(DNSRecord):
#     pass

# class DNSDMARCRecord(DNSRecord):
#     pass
