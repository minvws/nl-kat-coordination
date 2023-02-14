from typing import Dict, BinaryIO
from django.conf import settings

import requests
import time

from rocky.health import ServiceHealth


class ReportNotFoundException(Exception):
    pass


class KeikoClient:
    def __init__(self, base_uri: str):
        self.session = requests.Session()
        self._base_uri = base_uri

    def generate_report(self, template: str, data: Dict, glossary: str) -> str:
        res = self.session.post(
            f"{self._base_uri}/reports",
            json={
                "template": template,
                "data": data,
                "glossary": glossary,
            },
        )
        res.raise_for_status()
        return res.json()["report_id"]

    def get_report(self, report_id: str) -> BinaryIO:

        # try max 15 times to get the report, 1 second interval
        for i in range(15):
            time.sleep(1)
            res = self.session.get(f"{self._base_uri}/reports/{report_id}.keiko.pdf", stream=True)
            if res.status_code == 200:
                return res.raw
        res.raise_for_status()
        raise ReportNotFoundException

    def health(self) -> ServiceHealth:
        res = self.session.get(f"{self._base_uri}/health")
        res.raise_for_status()
        return ServiceHealth.parse_obj(res.json())


keiko_client = KeikoClient(settings.KEIKO_API)
