import typing
from functools import wraps
from typing import Any, Callable, Dict, Optional

import requests
from requests.models import HTTPError

from scheduler.connectors.errors import exception_handler
from scheduler.models import BoefjeMeta

from .services import HTTPService

ClientSessionMethod = Callable[..., Any]


def retry_with_login(function: ClientSessionMethod) -> ClientSessionMethod:
    @wraps(function)
    def wrapper(self, *args, **kwargs):  # type: ignore
        try:
            return function(self, *args, **kwargs)
        except HTTPError as error:
            if error.response.status_code != 401:
                raise error from HTTPError

            self.login()
            return function(self, *args, **kwargs)

    return typing.cast(ClientSessionMethod, wrapper)


class Bytes(HTTPService):
    """A class that provides methods to interact with the Bytes API."""

    name = "bytes"

    def __init__(self, host: str, source: str, user: str, password: str, timeout: int = 5):
        """Initialize the Bytes service.

        Args:
            host: A string representing the host.
            source: A string representing the source.
            user: A string representing the username.
            password: A string representing the password.
            timeout: An integer representing the timeout.
        """
        self.credentials: Dict[str, str] = {
            "username": user,
            "password": password,
        }

        super().__init__(host=host, source=source, timeout=timeout)

    def login(self) -> None:
        self.headers.update({"Authorization": f"bearer {self._get_token()}"})

    @staticmethod
    def _verify_response(response: requests.Response) -> None:
        response.raise_for_status()

    def _get_token(self) -> str:
        url = f"{self.host}/token"
        response = self.post(
            url=url,
            payload=self.credentials,
        )

        self._verify_response(response)

        return str(response.json()["access_token"])

    @retry_with_login
    @exception_handler
    def get_last_run_boefje(self, boefje_id: str, input_ooi: str, organization_id: str) -> Optional[BoefjeMeta]:
        url = f"{self.host}/bytes/boefje_meta"
        response = self.get(
            url=url,
            params={
                "boefje_id": boefje_id,
                "input_ooi": input_ooi,
                "organization": organization_id,
                "limit": 1,
                "descending": "true",
            },
        )

        self._verify_response(response)

        if response.status_code == 200 and len(response.json()) > 0:
            return BoefjeMeta(**response.json()[0])

        return None

    @retry_with_login
    @exception_handler
    def get_last_run_boefje_by_organisation_id(self, organization_id: str) -> Optional[BoefjeMeta]:
        url = f"{self.host}/bytes/boefje_meta"
        response = self.get(
            url=url,
            params={
                "organization": organization_id,
                "limit": 1,
                "descending": "true",
            },
        )

        self._verify_response(response)

        if response.status_code == 200 and response.content:
            return BoefjeMeta(**response.json()[0])

        return None
