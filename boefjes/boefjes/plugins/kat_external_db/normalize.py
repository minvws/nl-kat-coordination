import json
import logging
from ipaddress import IPv4Interface, ip_interface
from typing import Iterator, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, IPV4NetBlock, IPV6NetBlock, Network

# Expects raw to be json containing a list of ip_addresses/netblocks
# (as dictionaries) and a list of domains (as dictionaries).
# The paths through the dictionaries (to the lists and through the lists)
# are defined below.
# T O D O add these variables as normalizer settings in UI.
IP_ADDRESS_LIST_PATH = ["ip_addresses"]
IP_ADDRESS_ITEM_PATH = ["ip_address"]
DOMAIN_LIST_PATH = ["domains"]
DOMAIN_ITEM_PATH = ["domain"]


def follow_path_in_dict(path, path_dict):
    """Follows a list of keys in a dictionary recursively."""
    if path:
        key = path[0]
        if key not in path_dict:
            raise KeyError(f"Key {key} not in {list(path_dict.keys())}")
        return follow_path_in_dict(path=path[1:], path_dict=path_dict[key])
    return path_dict


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    """Yields hostnames, IPv4/6 addresses or netblocks."""
    results = json.loads(raw)
    network = Network(name=normalizer_meta.raw_data.boefje_meta.arguments["input"]["name"])
    y_addresses, y_blocks, y_hostnames = 0, 0, 0

    for address_item in follow_path_in_dict(path=IP_ADDRESS_LIST_PATH, path_dict=results):
        address = follow_path_in_dict(path=IP_ADDRESS_ITEM_PATH, path_dict=address_item)

        mask = None
        if "/" in address:
            address, mask = address.split("/")

        # Decide whether we yield IPv4 or IPv6.
        if isinstance(ip_interface(address), IPv4Interface):
            address_type = IPAddressV4
            block_type = IPV4NetBlock
        else:
            address_type = IPAddressV6
            block_type = IPV6NetBlock

        ip_address = address_type(address=address, network=network.reference)
        yield ip_address
        y_addresses += 1

        if mask is not None:
            yield block_type(
                start_ip=ip_address.reference,
                mask=int(mask),
                network=network.reference,
            )
            y_blocks += 1

    for hostname in follow_path_in_dict(path=DOMAIN_LIST_PATH, path_dict=results):
        yield Hostname(name=follow_path_in_dict(path=DOMAIN_ITEM_PATH, path_dict=hostname), network=network.reference)
        y_hostnames += 1

    logging.info(
        "Yielded %d IP addresses, %d netblocks and %d hostnames on %s.", y_addresses, y_blocks, y_hostnames, network
    )
