from bytes.version import __version__


def test_healthcheck(test_client) -> None:
    response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "bytes",
        "healthy": True,
        "version": __version__,
        "additional": None,
        "results": [],
    }
