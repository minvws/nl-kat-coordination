import sys
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

import httpx
from httpx import Client, HTTPTransport

from .boefje_handler import BoefjeHandler
from .interfaces import BoefjeOutput, BoefjeStorageInterface, Task
from .job_models import BoefjeMeta
from .repository import LocalPluginRepository


class CallbackStorageClient(BoefjeStorageInterface):
    def __init__(self, base_url: str, callback_url: str, outgoing_request_timeout: int):
        self._session = Client(base_url=base_url, transport=HTTPTransport(retries=6), timeout=outgoing_request_timeout)
        self.callback_url = callback_url

    def save_output(self, boefje_meta: BoefjeMeta, boefje_output: BoefjeOutput) -> dict[str, UUID]:
        response = self._session.post(self.callback_url, json=boefje_output.model_dump())
        response.raise_for_status()

        return response.json()


def run_with_callback(input_url: str):
    try:
        boefje_input = httpx.get(input_url).json()
        task = Task.model_validate(boefje_input["task"])
    except httpx.HTTPError as e:
        # sys.exit will print the message on stderr and return with exit code 1
        sys.exit(f"Failed to get input from boefje API (at {input_url}): {e}")

    parsed = urlparse(input_url)
    client = CallbackStorageClient(f"{parsed.scheme}://{parsed.netloc}", boefje_input["output_url"], 30)
    handler = BoefjeHandler(LocalPluginRepository(Path()), client)

    try:
        handler.handle(task)
    except httpx.HTTPError as e:
        sys.exit(f"Failed to handle task: {e}")
