import json
import socket
from ipaddress import ip_network
from typing import List, Tuple, Union

from boefjes.job_models import BoefjeMeta


def run_rdns(cidr):
    network = ip_network(cidr)
    results = []

    for ip in network.hosts():
        ptr_value = get_ptr_record(str(ip))
        data = {"IP": f"{ip}", "PTR": f"{ptr_value}"}
        results.append(data)
    return results


def get_ptr_record(ip_address):
    try:
        ptr_record = socket.gethostbyaddr(ip_address)[0]
    except socket.herror:
        return None
    return ptr_record


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    """return results to normalizer."""
    try:
        ip_range = (
            f"{boefje_meta.arguments['input']['start_ip']['address']}/{str(boefje_meta.arguments['input']['mask'])}"
        )
        results = run_rdns(ip_range)
    except KeyError:
        try:
            ip = boefje_meta.arguments["input"]["address"]
            results = run_rdns(ip)
        except KeyError:
            return None
    return [(set(), json.dumps(results, default=str))]
