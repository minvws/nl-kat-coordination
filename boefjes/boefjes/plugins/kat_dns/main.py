"""Boefje script for getting dns records"""

import json
import logging
import re
from os import getenv

import dns.resolver
from dns.edns import EDEOption
from dns.name import Name
from dns.resolver import Answer

logger = logging.getLogger(__name__)
DEFAULT_RECORD_TYPES = {
    "A",
    "AAAA",
    "CAA",
    "CERT",
    "RP",
    "SRV",
    "TXT",
    "MX",
    "NS",
    "CNAME",
    "DNAME",
    "SOA",
    "LOC",
    "GPOS",
}


class TimeoutException(Exception):
    pass


class ZoneNotFoundException(Exception):
    pass


def get_record_types() -> set[str]:
    requested_record_types = getenv("RECORD_TYPES", "")
    if not requested_record_types:
        return DEFAULT_RECORD_TYPES
    parsed_requested_record_types = map(
        lambda x: re.sub(r"[^A-Za-z]", "", x), requested_record_types.upper().split(",")
    )
    return set(parsed_requested_record_types).intersection(DEFAULT_RECORD_TYPES)


def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    hostname = boefje_meta["arguments"]["input"]["name"]

    requested_dns_name = dns.name.from_text(hostname)
    resolver = dns.resolver.Resolver()
    # https://dnspython.readthedocs.io/en/stable/_modules/dns/edns.html
    # enable EDE to get the DNSSEC Bogus return values if the server supports it # codespell-ignore
    resolver.use_edns(options=[EDEOption(15)])
    nameserver = getenv("REMOTE_NS", "1.1.1.1")
    resolver.nameservers = [nameserver]

    record_types = get_record_types()
    answers = [get_parent_zone_soa(resolver, requested_dns_name)] if "SOA" in record_types else []

    for type_ in record_types:
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
    if not answers_formatted and results["dmarc_response"] == "Timeout" and results["dkim_response"] == "Timeout":
        raise TimeoutException("No answers from DNS-Server due to timeouts.")
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
    except dns.resolver.NoNameservers as error:
        # dnspython stores (server, tcp, port, reason, response) tuples.
        # A SERVFAIL response is not required to contain an EDE option (RFC 8914).
        for failure in error.kwargs.get("errors", []):
            if len(failure) < 5 or failure[3] != "SERVFAIL" or failure[4] is None:
                continue
            for option in getattr(failure[4], "options", ()):
                # DNSSEC error codes defined in RFC 8914
                if isinstance(option, EDEOption) and int(option.code) in (1, 2, 5, 6, 7, 8, 9, 10, 11, 12): # DNSSEC error codes defined in RFC 8914
                    return "DNSSECFAIL"
        # Keep the rest of the scan usable when a query fails without EDE.
        logger.warning("No DNS nameserver could answer %s.%s", record_subdomain, hostname)
        return "SERVFAIL"
    except dns.resolver.NXDOMAIN:
        return "NXDOMAIN"
    except dns.resolver.Timeout:
        return "Timeout"
