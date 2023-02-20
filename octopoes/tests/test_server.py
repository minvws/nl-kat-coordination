from unittest.mock import Mock

from requests import HTTPError

from octopoes.server import Server


def test_server_health(app_context):
    mock_ingester = Mock()
    mock_ingester.xtdb_client.status.return_value = "OK"
    server = Server(app_context, {"test_ingester": mock_ingester})

    response = server.health()
    assert response.dict() == {
        "additional": None,
        "externals": {"Katalogus": True, "test_ingester": True},
        "healthy": True,
        "results": [],
        "service": "octopoes",
        "version": "0.1.0",
    }


def test_server_health_xtdb_unhealthy(app_context):
    mock_ingester = Mock()
    mock_ingester.xtdb_client.status.side_effect = HTTPError
    server = Server(app_context, {"test_ingester": mock_ingester})

    response = server.health()
    assert response.dict() == {
        "additional": None,
        "externals": {"Katalogus": True, "test_ingester": False},
        "healthy": False,
        "results": [],
        "service": "octopoes",
        "version": "0.1.0",
    }
