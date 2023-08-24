from typing import List, Tuple, Union

import dns
from dns.resolver import Answer

from boefjes.config import settings
from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    """return results to normalizer."""
    ip = boefje_meta.arguments["input"]["address"]

    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [str(settings.remote_ns)]
        reverse_ip = dns.reversename.from_address(ip)
        answer: Answer = resolver.resolve(reverse_ip, "PTR")
        result = f"RESOLVER: {answer.nameserver}\n{answer.response}"
        return [(set(), result)]
    except dns.resolver.NXDOMAIN:
        return [(set(), "NXDOMAIN")]
    except (dns.resolver.Timeout, dns.resolver.NoAnswer):
        return [(set(), "NoAnswer")]
