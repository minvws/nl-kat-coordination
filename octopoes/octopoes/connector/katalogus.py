from typing import List

import requests


class KATalogusClientV1:
    def __init__(self, base_uri: str):
        self.base_uri = f"{base_uri.rstrip('/')}/v1"

    def get_organisations(self) -> List[str]:
        response = requests.get(f"{self.base_uri}/organisations", timeout=30)
        response.raise_for_status()

        return response.json().keys()
