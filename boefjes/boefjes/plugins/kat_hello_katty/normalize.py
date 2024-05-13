import json
from collections.abc import Iterable
from ipaddress import AddressValueError, IPv4Network, NetmaskValueError

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, Network
from octopoes.models.ooi.greeting import Greeting


def is_ipv4(string: str) -> bool:
    try:
        IPv4Network(string)
        return True
    except (AddressValueError, NetmaskValueError, ValueError) as e:
        return False


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    """Function that gets ran to produce OOIs from the boefje it consumes"""

    data_string = str(raw, "utf-8")
    data: dict = json.loads(data_string)

    network = Network(
        name=normalizer_meta.raw_data.boefje_meta.arguments["input"]["network"]["name"])
    yield network

    ip = None
    if is_ipv4(data["address"]):
        ip = IPAddressV4(network=network.reference, address=data["address"])
    else:
        ip = IPAddressV6(network=network.reference, address=data["address"])

    yield ip
    yield Greeting(address=ip.reference, greeting=data["greeting"])
