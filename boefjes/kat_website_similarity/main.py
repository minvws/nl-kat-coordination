"""Boefje script checking if a website hosts the same website on IPv4 and IPv6"""
import json
import socket
from typing import Tuple, Union

import html_similarity
import requests
import requests.packages.urllib3.util.connection as urllib3_cn

from job import BoefjeMeta


def allowed_gai_family_ipv4():
    return socket.AF_INET  # force ipv4


def allowed_gai_family_ipv6():
    family = socket.AF_INET
    if urllib3_cn.HAS_IPV6:
        family = socket.AF_INET6  # force ipv6 only if it is available
    return family


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    input_ = boefje_meta.arguments["input"]
    hostname = input_["name"]
    url = "http://" + hostname

    urllib3_cn.allowed_gai_family = allowed_gai_family_ipv4
    try:
        resp4 = requests.get(url).text
        if "</body>" in resp4:
            compare_resp4 = resp4.split("<body")[1].split("</body>")[0]
    except requests.exceptions.ConnectionError:
        return boefje_meta, json.dumps({})

    urllib3_cn.allowed_gai_family = allowed_gai_family_ipv6
    try:
        resp6 = requests.get(url).text
        if "</body>" in resp6:
            compare_resp6 = resp6.split("<body")[1].split("</body>")[0]
    except requests.exceptions.ConnectionError:
        return boefje_meta, json.dumps({})

    similarity = (
        html_similarity.similarity(compare_resp4, compare_resp6)
        if "</body>" in resp4 and "</body>" in resp6
        else float(resp4 == resp6)
    )

    result = {
        "website_similarity": similarity,
        "website_html_ipv4": resp4,
        "website_html_ipv6": resp6,
    }

    return boefje_meta, json.dumps(result)
