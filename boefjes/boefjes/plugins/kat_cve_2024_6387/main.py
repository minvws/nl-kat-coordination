"""
CVE-2024-6387 checker
Author: Mischa van Geelen <@rickgeex>

"""

import json
import socket

from boefjes.job_models import BoefjeMeta

TIMEOUT = 1.0


class SSHChecker:
    vulnerable_versions = [
        "SSH-2.0-OpenSSH_8.5",
        "SSH-2.0-OpenSSH_8.6",
        "SSH-2.0-OpenSSH_8.7",
        "SSH-2.0-OpenSSH_8.8",
        "SSH-2.0-OpenSSH_8.9",
        "SSH-2.0-OpenSSH_9.0",
        "SSH-2.0-OpenSSH_9.1",
        "SSH-2.0-OpenSSH_9.2",
        "SSH-2.0-OpenSSH_9.3",
        "SSH-2.0-OpenSSH_9.4",
        "SSH-2.0-OpenSSH_9.5",
        "SSH-2.0-OpenSSH_9.6",
        "SSH-2.0-OpenSSH_9.7",
    ]

    excluded_versions = [
        "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.10",
        "SSH-2.0-OpenSSH_9.3p1 Ubuntu-3ubuntu3.6",
        "SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13.3",
        "SSH-2.0-OpenSSH_9.3p1 Ubuntu-1ubuntu3.6",
        "SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u3",
        "SSH-2.0-OpenSSH_8.4p1 Debian-5+deb11u3",
    ]

    def __init__(self, ip, port, timeout):
        self.ip = ip
        self.port = port
        self.timeout = timeout

    def get_ssh_sock(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.ip, self.port))
            return sock
        except Exception:
            return None

    def get_ssh_banner(self, sock):
        try:
            banner = sock.recv(1024)
            try:
                banner = banner.decode().strip()
            except UnicodeDecodeError:
                banner = banner.decode("latin1").strip()
            sock.close()
            return banner
        except Exception as e:
            return str(e)

    def check_vulnerability(self) -> tuple[str, str]:
        sshsock = self.get_ssh_sock()
        if not sshsock:
            return "closed", "Port is closed"

        banner = self.get_ssh_banner(sshsock)
        if "SSH-2.0-OpenSSH" not in banner:
            return "failed", banner

        if (
            any(version in banner for version in SSHChecker.vulnerable_versions)
            and banner not in SSHChecker.excluded_versions
        ):
            return "vulnerable", banner
        else:
            return "not_vulnerable", banner


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, str | bytes]]:
    input_ = boefje_meta.arguments["input"]  # input is IPPort
    port = input_["port"]
    ip = input_["address"]["address"]

    status, banner = SSHChecker(ip, port, TIMEOUT).check_vulnerability()

    return [(set(), json.dumps({"status": status, "banner": banner}))]
