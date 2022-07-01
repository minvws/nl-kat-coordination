"""Boefje script for getting dns records"""
import logging
from typing import Union, Tuple

import dns.resolver
from dns.name import Name
from dns.resolver import Answer

from job import BoefjeMeta

logger = logging.getLogger(__name__)


class ZoneNotFoundException(Exception):
    pass


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:

    hostname = boefje_meta.arguments["input"]["name"]

    requested_dns_name = dns.name.from_text(hostname)
    zone_soa_record = get_parent_zone_soa(requested_dns_name)

    answers = [
        zone_soa_record,
    ]

    dns_record_types = ["A", "AAAA", "TXT", "MX", "NS", "CNAME", "DNAME"]
    for type_ in dns_record_types:

        try:
            answer: Answer = dns.resolver.resolve(hostname, type_)
            answers.append(answer)
        except dns.resolver.NoAnswer:
            pass
        except dns.resolver.NXDOMAIN:
            return boefje_meta, "NXDOMAIN"
        except dns.resolver.Timeout:
            pass

    answers_formatted = [
        f"RESOLVER: {answer.nameserver}\n{answer.response}" for answer in answers
    ]

    return boefje_meta, "\n\n".join(answers_formatted)


def get_parent_zone_soa(name: Name) -> Answer:
    while True:

        try:
            return dns.resolver.resolve(name, dns.rdatatype.SOA)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            pass

        try:
            name = name.parent()
        except dns.name.NoParent:
            raise ZoneNotFoundException
