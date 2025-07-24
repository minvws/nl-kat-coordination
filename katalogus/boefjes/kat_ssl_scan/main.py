import docker

SSLSCAN_IMAGE = "breezethink/sslscan:latest"


def run(input_ooi: dict, boefje: dict) -> list[tuple[set, bytes | str]]:
    client = docker.from_env()
    input_ = input_ooi
    hostname = input_["hostname"]["name"]

    scheme = input_["ip_service"]["service"]["name"]
    if scheme != "https":
        return [({"info/boefje"}, "Skipping check due to non-TLS scheme")]

    output = client.containers.run(SSLSCAN_IMAGE, ["--xml=-", hostname], remove=True)

    return [(set(), output)]
