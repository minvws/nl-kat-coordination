from unittest import TestCase

from boefjes.plugins.kat_nmap.main import Protocol, build_nmap_arguments


class NmapTest(TestCase):
    def test_nmap_arguments_tcp_top_150(self):
        args = build_nmap_arguments("1.1.1.1", Protocol.TCP, 250)
        self.assertListEqual(
            [
                "nmap",
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
                "nmap",
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
                "nmap",
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
                "nmap",
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
                "nmap",
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
                "nmap",
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
                "nmap",
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
                "nmap",
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
