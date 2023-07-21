"""Boefje script for getting dns records"""
import json
import logging
from typing import List, Tuple, Union

import dns.resolver
from dns.name import Name
from dns.resolver import Answer

from boefjes.config import settings
from boefjes.job_models import BoefjeMeta
from boefjes.utils import BoefjeOutput, Channel

logger = logging.getLogger(__name__)

boefje_output = BoefjeOutput()


class ZoneNotFoundException(Exception):
    pass


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    hostname = boefje_meta.arguments["input"]["name"]

    requested_dns_name = dns.name.from_text(hostname)
    zone_soa_record = get_parent_zone_soa(requested_dns_name)

    answers = [
        zone_soa_record,
    ]

    dns_record_types = ["A", "AAAA", "TXT", "MX", "NS", "CNAME", "DNAME"]
    for type_ in dns_record_types:
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [settings.remote_ns]
            answer: Answer = resolver.resolve(hostname, type_)
            answers.append(answer)
        except dns.resolver.NoAnswer:
            pass
        except dns.resolver.NXDOMAIN:
            return boefje_output.format(set(), "NXDOMAIN")
        except dns.resolver.Timeout:
            pass

    answers_formatted = [f"RESOLVER: {answer.nameserver}\n{answer.response}" for answer in answers]

    results = {
        "dns_records": "\n\n".join(answers_formatted),
        "dmarc_response": get_email_security_records(hostname, "_dmarc"),
        "dkim_response": get_email_security_records(hostname, "_domainkey"),
    }

    boefje_output.writeln(Channel.DEBUG, "This is a debug message.")
    boefje_output.writeln(Channel.DEBUG, "This is another debug message.")
    boefje_output.writeln(Channel.INFO, "This is some info! :O !")

    return boefje_output.format(set(), json.dumps(results))


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


def get_email_security_records(hostname: str, record_subdomain: str) -> str:
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [settings.remote_ns]
        answer = resolver.resolve(f"{record_subdomain}.{hostname}", "TXT", raise_on_no_answer=False)
        return answer.response.to_text()
    except dns.resolver.NXDOMAIN:
        return "NXDOMAIN"
    except dns.resolver.Timeout:
        return "Timeout"
