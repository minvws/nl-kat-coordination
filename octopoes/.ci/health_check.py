"""Health check script for the integration tests."""
import http
import sys
import urllib.request


def check_health(url: str) -> None:
    """Check if the server is up and running."""
    with urllib.request.urlopen(url) as response:
        if response.status != http.HTTPStatus.OK:
            sys.exit(1)


if __name__ == "__main__":
    check_health(sys.argv[1])
