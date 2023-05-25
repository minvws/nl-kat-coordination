
from typing import List, Tuple, Union
from boefjes.job_models import BoefjeMeta
import socket
import json


def run_rdns(ip_address: List[str]) -> str:
    """Reverse DNS Lookup"""
    # Disable caching
    socket.setdefaulttimeout(0)
    # Perform a rDNS lookup for the IP address
    try: 
        hostname = socket.gethostbyaddr(ip_address)[0]
    except socket.herror:
        print(f"Could not resolve hostname for {ip_address}")
    else:
        data = {
                "IP-Address": ip_address,
                "Hostname": hostname
                }
        return data


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    """return results to normalizer."""
    input_ = boefje_meta.arguments["input"]
    ip_address = input_["address"]
    results = run_rdns(ip_address)
    return [(set(), json.dumps(results))]
