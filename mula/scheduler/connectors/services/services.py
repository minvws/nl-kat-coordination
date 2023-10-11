import logging
import urllib.parse
from typing import Any, Dict, MutableMapping, Optional, Union

import requests
from requests.adapters import HTTPAdapter, Retry

from ..connector import Connector  # noqa: TID252


class HTTPService(Connector):
    """HTTPService exposes methods to make http requests to services that
    typically expose rest api endpoints

    Attributes:
        logger:
            The logger for the class.
        session:
            A requests.Session object.
        name:
            A string describing the name of the service. This is used args
            an identifier.
        source:
            As string defining the request user agent of HTTP request made from
            this HTTPService instance. This helps services differentiate from
            where the requests came from.
        host:
            A string url formatted reference to the host of the service
        headers:
            A dict containing the request headers.
        health_endpoint:
            A string defining the health endpoint for the service. Used too
            determine whether a host is healthy.
        timeout:
            An integer defining the timeout of requests.
    """

    name: Optional[str] = None
    health_endpoint: Optional[str] = "health"

    def __init__(self, host: str, source: str, timeout: int = 5, retries: int = 5):
        """Initializer of the HTTPService class. During initialization the
        host will be checked if it is available and healthy.

        Args:
            host:
                A string url formatted reference to the host of the service
            source:
                A string defining the request source of HTTP request made from
                this HTTPService instance. This helps services differentiate
                from where the requests came from.
            timeout:
                An integer defining the timeout of requests.
            retries:
                An integer defining the number of retries to make before
                giving up.
        """
        super().__init__()

        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        self.session: requests.Session = requests.Session()
        self.host: str = host
        self.timeout: int = timeout
        self.retries = retries
        self.source: str = source

        max_retries = Retry(
            total=self.retries,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504],
        )
        self.session.mount("http://", HTTPAdapter(max_retries=max_retries))
        self.session.mount("https://", HTTPAdapter(max_retries=max_retries))

        if self.source:
            self.headers["User-Agent"] = self.source

        self._do_checks()

    def get(
        self,
        url: str,
        payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """Execute a HTTP GET request

        Args:
            headers:
                A dict to set additional headers for the request.
            params:
                A dict to set the query parameters for the request

        Returns:
            A request.Response object
        """
        response = self.session.get(
            url,
            headers=self.headers,
            params=params,
            data=payload,
            timeout=self.timeout,
        )
        self.logger.debug(
            "Made GET request to %s. [name=%s, url=%s]",
            url,
            self.name,
            url,
        )

        return response

    def post(
        self,
        url: str,
        payload: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """Execute a HTTP POST request

        Args:
            headers:
                A dict to set additional headers for the request.
            params:
                A dict to set the query parameters for the request

        Returns:
            A request.Response object
        """
        response = self.session.post(
            url,
            headers=self.headers,
            params=params,
            data=payload,
            timeout=self.timeout,
        )
        self.logger.debug(
            "Made POST request to %s. [name=%s, url=%s, data=%s]",
            url,
            self.name,
            url,
            payload,
        )

        self._verify_response(response)

        return response

    @property
    def headers(self) -> MutableMapping[str, Union[str, bytes]]:
        return self.session.headers

    def _do_checks(self) -> None:
        """Do checks whether a host is available and healthy."""
        parsed_url = urllib.parse.urlparse(self.host)
        hostname, port = parsed_url.hostname, parsed_url.port

        if port is None and parsed_url.scheme is not None:
            port = 80 if parsed_url.scheme == "http" else 443

        if hostname is None or port is None:
            self.logger.warning(
                "Not able to parse hostname and port from %s [host=%s]",
                self.host,
                self.host,
            )
            return

        if self.host is not None and self.retry(self.is_host_available, hostname, port) is False:
            raise RuntimeError(f"Host {self.host} is not available.")

        if self.health_endpoint is not None and self.retry(self.is_healthy) is False:
            raise RuntimeError(f"Service {self.name} is not running.")

    def is_healthy(self) -> bool:
        """Check if host is healthy by inspecting the host's health endpoint.

        Returns:
            A boolean
        """
        if self.host is None:
            self.logger.warning("Host is not set.")
            return False

        if self.health_endpoint is None:
            self.logger.warning("Health endpoint is not set.")
            return False

        return self.is_host_healthy(self.host, self.health_endpoint)

    def _verify_response(self, response: requests.Response) -> None:
        """Verify the received response from a request.

        Raises:
            Exception
        """
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            self.logger.error(
                "Received bad response from %s. [name=%s, url=%s, response=%s]",
                response.url,
                self.name,
                response.url,
                str(response.content),
            )
            raise e
