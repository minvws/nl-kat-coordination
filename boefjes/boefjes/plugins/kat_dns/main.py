"""Boefje script for getting dns records"""
import json
import logging
import re
from os import getenv
from typing import List, Tuple, Union

import dns.resolver
from dns.name import Name
from dns.resolver import Answer

from boefjes.config import settings
from boefjes.job_models import BoefjeMeta

logger = logging.getLogger(__name__)
DEFAULT_RECORD_TYPES = set(("A", "AAAA", "CAA", "CERT", "RP", "SRV", "TXT", "MX", "NS", "CNAME", "DNAME"))


class ZoneNotFoundException(Exception):
    pass


def get_record_types() -> List[str]:
    requested_record_types = getenv("RECORD_TYPES", "")
    if not requested_record_types:
        return DEFAULT_RECORD_TYPES
    requested_record_types = list(map(lambda x: re.sub(r"[^A-Za-z]", "", x), requested_record_types.upper().split(",")))
    return list(set(requested_record_types).intersection(DEFAULT_RECORD_TYPES))


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    hostname = boefje_meta.arguments["input"]["name"]

    requested_dns_name = dns.name.from_text(hostname)
    resolver = dns.resolver.Resolver()
    nameserver = getenv("REMOTE_NS", str(settings.remote_ns))
    resolver.nameservers = [nameserver]

    answers = [
        get_parent_zone_soa(resolver, requested_dns_name),
    ]

    for type_ in get_record_types():
        try:
            answer: Answer = resolver.resolve(hostname, type_)
            answers.append(answer)
        except (dns.resolver.NoAnswer, dns.resolver.Timeout):
            pass
        except dns.resolver.NXDOMAIN:
            return [(set(), "NXDOMAIN")]

    answers_formatted = [f"RESOLVER: {answer.nameserver}\n{answer.response}" for answer in answers]

    results = {
        "dns_records": "\n\n".join(answers_formatted),
        "dmarc_response": get_email_security_records(resolver, hostname, "_dmarc"),
        "dkim_response": get_email_security_records(resolver, hostname, "_domainkey"),
    }
    return [(set(), json.dumps(results))]


def get_parent_zone_soa(resolver: dns.resolver.Resolver, name: Name) -> Answer:
    while True:
        try:
            return resolver.resolve(name, dns.rdatatype.SOA)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            pass

        try:
            name = name.parent()
        except dns.name.NoParent:
            raise ZoneNotFoundException


def get_email_security_records(resolver: dns.resolver.Resolver, hostname: str, record_subdomain: str) -> str:
    try:
        answer = resolver.resolve(f"{record_subdomain}.{hostname}", "TXT", raise_on_no_answer=False)
        return answer.response.to_text()
    except dns.resolver.NXDOMAIN:
        return "NXDOMAIN"
    except dns.resolver.Timeout:
        return "Timeout"
