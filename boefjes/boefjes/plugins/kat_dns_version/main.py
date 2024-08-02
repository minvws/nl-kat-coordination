"""Boefje script for getting namserver version"""

import json
import logging
from os import getenv

import dns

from boefjes.job_models import BoefjeMeta

logger = logging.getLogger(__name__)


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, str | bytes]]:
    input_ = boefje_meta.arguments["input"]  # input is IPService
    ip_port = input_["ip_port"]
    if input_["service"]["name"] != "dns":
        return [({"boefje/error"}, "Not a DNS service")]

    ip = ip_port["address"]["address"]
    port = ip_port["port"]
    protocol = ip_port["protocol"]

    timeout = float(getenv("TIMEOUT", 30))

    method = dns.query.tcp
    if protocol == "udp":
        method = dns.query.udp

    queries = [
        dns.message.make_query("VERSION.BIND", dns.rdatatype.TXT, dns.rdataclass.CHAOS),
        dns.message.make_query("VERSION.SERVER", dns.rdatatype.TXT, dns.rdataclass.CHAOS),
    ]

    results = []
    for query in queries:
        response = method(query, where=ip, timeout=timeout, port=port)

        try:
            answer = response.answer[0]
            results.append(answer.to_rdataset().pop().strings[0].decode())
        except IndexError:
            pass

    return [(set(), json.dumps(results))]
