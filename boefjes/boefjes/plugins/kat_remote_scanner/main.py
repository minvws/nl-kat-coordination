import os


def run(boefje_meta: dict):
    cmd = os.getenv("COMMAND", "echo no command given")
    return [(set(), f"{cmd} has been ran!")]


"""echo $PWD
from ipaddress import ip_address
import socket
hostname = socket.gethostname()
IPAddr = socket.gethostbyname(hostname)
ip = ip_address(boefje_meta["arguments"]["website"]["ip_service"]["ip_port"]["address"]["address"])
return [(set(), f"{hostname};;{IPAddr};;{ip.exploded}")]
"""
