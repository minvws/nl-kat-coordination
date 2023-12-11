from unittest import TestCase

from tests.loading import get_boefje_meta, get_dummy_data, get_normalizer_meta

from boefjes.job_handler import serialize_ooi
from boefjes.plugins.kat_nmap_tcp.main import Protocol, build_nmap_arguments
from boefjes.plugins.kat_nmap_tcp.normalize import run
from octopoes.models.ooi.network import IPAddressV4, Network


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
        input_ooi = IPAddressV4(network=Network(name="internet").reference, address="134.209.85.72")
        boefje_meta = get_boefje_meta(input_ooi=input_ooi.reference)
        boefje_meta.arguments["input"] = serialize_ooi(input_ooi)
        output = list(run(get_normalizer_meta(boefje_meta), get_dummy_data("raw/nmap_mispoes.xml")))
        self.assertEqual(17, len(output))
        for i, out in enumerate(output[:-1]):
            if out.object_type == "IPPort" and output[i + 1].object_type == "Service":
                if out.port == 80:
                    self.assertEqual("http", output[i + 1].name)
                elif out.port == 443:
                    self.assertEqual("https", output[i + 1].name)
                else:
                    self.assertNotEqual("http", output[i + 1].name)
                    self.assertNotEqual("https", output[i + 1].name)
