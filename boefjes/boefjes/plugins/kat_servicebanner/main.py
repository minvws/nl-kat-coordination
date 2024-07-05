import socket

from boefjes.job_models import BoefjeMeta

TIMEOUT = 1.0


def get_ssh_sock(ip, port, timeout):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((ip, port))
        return sock
    except Exception:
        return None


def get_ssh_banner(sock):
    try:
        banner = sock.recv(1024)
        try:
            banner = banner.decode().strip()
        except UnicodeDecodeError:
            banner = banner.decode("latin1").strip()
        sock.close()
        return [({"openkat/servicebanner"}, banner)]
    except Exception as e:
        return [({"boefje/error"}, f"Unable to get SSH banner. {str(e)}")]


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, str | bytes]]:
    input_ = boefje_meta.arguments["input"]  # input is IPPort
    port = input_["port"]
    ip = input_["address"]["address"]

    sshsock = get_ssh_sock(ip, port, TIMEOUT)

    return get_ssh_banner(sshsock)
