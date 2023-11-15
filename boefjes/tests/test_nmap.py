from unittest import TestCase

from pydantic import parse_obj_as

from boefjes.job_handler import serialize_ooi
from boefjes.plugins.kat_nmap.main import Protocol, build_nmap_arguments
from boefjes.plugins.kat_nmap.normalize import run
from octopoes.models.types import OOIType
from tests.loading import get_boefje_meta, get_dummy_data, get_normalizer_meta


class NmapTest(TestCase):
    def test_nmap_arguments_tcp_top_150(self):
        args = build_nmap_arguments("1.1.1.1", Protocol.TCP, 250)
        self.assertListEqual(
            [
                "--open",
                "-T4",
                "-Pn",
                "-r",
                "-v10",
                "-sV",
                "-sS",
                "--top-ports",
                "250",
                "-oX",
                "-",
                "1.1.1.1",
            ],
            args,
        )

    def test_nmap_arguments_tcp_top_150_ipv6(self):
        args = build_nmap_arguments("2001:19f0:5001:23fe:5400:3ff:fe60:883b", Protocol.TCP, 250)
        self.assertListEqual(
            [
                "--open",
                "-T4",
                "-Pn",
                "-r",
                "-v10",
                "-sV",
                "-sS",
                "--top-ports",
                "250",
                "-6",
                "-oX",
                "-",
                "2001:19f0:5001:23fe:5400:3ff:fe60:883b",
            ],
            args,
        )

    def test_nmap_arguments_tcp_full(self):
        args = build_nmap_arguments("1.1.1.1", Protocol.TCP, None)
        self.assertListEqual(
            [
                "--open",
                "-T4",
                "-Pn",
                "-r",
                "-v10",
                "-sV",
                "-sS",
                "-p-",
                "-oX",
                "-",
                "1.1.1.1",
            ],
            args,
        )

    def test_nmap_arguments_tcp_full_ipv6(self):
        args = build_nmap_arguments("2001:19f0:5001:23fe:5400:3ff:fe60:883b", Protocol.TCP, None)
        self.assertListEqual(
            [
                "--open",
                "-T4",
                "-Pn",
                "-r",
                "-v10",
                "-sV",
                "-sS",
                "-p-",
                "-6",
                "-oX",
                "-",
                "2001:19f0:5001:23fe:5400:3ff:fe60:883b",
            ],
            args,
        )

    def test_nmap_arguments_udp_full(self):
        args = build_nmap_arguments("1.1.1.1", Protocol.UDP, None)
        self.assertListEqual(
            [
                "--open",
                "-T4",
                "-Pn",
                "-r",
                "-v10",
                "-sV",
                "-sU",
                "-p-",
                "-oX",
                "-",
                "1.1.1.1",
            ],
            args,
        )

    def test_nmap_arguments_udp_full_ipv6(self):
        args = build_nmap_arguments("2001:19f0:5001:23fe:5400:3ff:fe60:883b", Protocol.UDP, None)
        self.assertListEqual(
            [
                "--open",
                "-T4",
                "-Pn",
                "-r",
                "-v10",
                "-sV",
                "-sU",
                "-p-",
                "-6",
                "-oX",
                "-",
                "2001:19f0:5001:23fe:5400:3ff:fe60:883b",
            ],
            args,
        )

    def test_nmap_arguments_udp_top250(self):
        args = build_nmap_arguments("1.1.1.1", Protocol.UDP, 250)
        self.assertListEqual(
            [
                "--open",
                "-T4",
                "-Pn",
                "-r",
                "-v10",
                "-sV",
                "-sU",
                "--top-ports",
                "250",
                "-oX",
                "-",
                "1.1.1.1",
            ],
            args,
        )

    def test_nmap_arguments_udp_top250_ipv6(self):
        args = build_nmap_arguments("2001:19f0:5001:23fe:5400:3ff:fe60:883b", Protocol.UDP, 250)
        self.assertListEqual(
            [
                "--open",
                "-T4",
                "-Pn",
                "-r",
                "-v10",
                "-sV",
                "-sU",
                "--top-ports",
                "250",
                "-6",
                "-oX",
                "-",
                "2001:19f0:5001:23fe:5400:3ff:fe60:883b",
            ],
            args,
        )

    def test_normalizer(self):
        input_ooi = parse_obj_as(
            OOIType,
            {
                "object_type": "IPAddressV4",
                "network": "Network|internet",
                "address": "134.209.85.72",
            },
        )
        boefje_meta = get_boefje_meta(input_ooi=input_ooi.reference)
        boefje_meta.arguments["input"] = serialize_ooi(input_ooi)
        output = [x for x in run(get_normalizer_meta(boefje_meta), get_dummy_data("raw/nmap_mispoes.xml"))]
        self.assertEqual(17, len(output))
