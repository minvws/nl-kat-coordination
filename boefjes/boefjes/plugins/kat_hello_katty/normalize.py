import json
from collections.abc import Iterable
from ipaddress import AddressValueError, IPv4Network, NetmaskValueError

from boefjes.job_models import NormalizerOutput
from octopoes.models.ooi.greeting import Greeting
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, Network


def is_ipv4(string: str) -> bool:
    try:
        IPv4Network(string)
        return True
    except (AddressValueError, NetmaskValueError, ValueError):
        return False


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    """Function that gets ran to produce OOIs from the boefje it consumes"""
    data_string = str(raw, "utf-8")
    data: dict = json.loads(data_string)

    network = Network(name=input_ooi["network"]["name"])
    yield network

    ip = None
    if is_ipv4(data["address"]):
        ip = IPAddressV4(network=network.reference, address=data["address"])
    else:
        ip = IPAddressV6(network=network.reference, address=data["address"])

    yield ip
    yield Greeting(address=ip.reference, greeting=data["greeting"])
