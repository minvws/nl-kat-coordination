from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

import sys
from httpx import HTTPTransport, Client

from .repository import LocalPluginRepository
from .interfaces import BoefjeStorageInterface, BoefjeOutput, Task
from .boefje_handler import  BoefjeHandler
import httpx


class CallbackStorageClient(BoefjeStorageInterface):
    def __init__(self, base_url: str, callback_url: str, outgoing_request_timeout: int):
        self._session = Client(base_url=base_url, transport=HTTPTransport(retries=6), timeout=outgoing_request_timeout)
        self.callback_url = callback_url

    def save_raws(self, boefje_meta_id: UUID, boefje_output: BoefjeOutput) -> dict[str, UUID]:
        response =  self._session.post(self.callback_url, json=boefje_output.model_dump())
        response.raise_for_status()

        return response.json()


def main():
    input_url = sys.argv[-1]
    try:
        boefje_input = httpx.get(input_url).json()
        task = Task.model_validate(boefje_input["task"])
    except httpx.HTTPError as e:
        # sys.exit will print the message on stderr and return with exit code 1
        sys.exit(f"Failed to get input from boefje API: {e}")

    parsed = urlparse(input_url)
    client = CallbackStorageClient(f"{parsed.scheme}://{parsed.netloc}", boefje_input["output_url"], 30)
    handler = BoefjeHandler(LocalPluginRepository(Path()), client)

    try:
        handler.handle(task)
    except httpx.HTTPError as e:
        sys.exit(f"Failed to handle task: {e}")


if __name__ == "__main__":
    main()
