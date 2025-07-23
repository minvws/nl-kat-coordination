import requests

API_URL = "https://admin.thegreenwebfoundation.org"


def run(input_ooi: dict, boefje: dict) -> list[tuple[set, bytes | str]]:
    input_ = input_ooi
    hostname = input_["hostname"]["name"]

    response = requests.get(f"{API_URL}/greencheck/{hostname}", timeout=30)

    return [(set(), response.content)]
