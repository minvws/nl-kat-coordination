import requests


def run(input_ooi: dict, boefje: dict) -> list[tuple[set, bytes | str]]:
    response = requests.get(
        "https://raw.githubusercontent.com/RetireJS/retire.js/v3/repository/jsrepository.json", timeout=30
    )

    return [(set(), response.content)]
