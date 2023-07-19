import pytest
import requests
from fastapi.testclient import TestClient

from octopoes.api.api import app
from octopoes.version import __version__

client = TestClient(app)


@pytest.fixture
def patch_pika(mocker):
    return mocker.patch("pika.BlockingConnection")


def test_health(requests_mock, patch_pika):
    crux_status = {
        "version": "21.05-1.17.0-beta",
        "revision": None,
        "indexVersion": 18,
        "consumerState": None,
        "kvStore": "crux.mem_kv.MemKv",
        "estimateNumKeys": 25,
        "size": None,
    }

    requests_mock.real_http = True
    requests_mock.get("http://crux:3000/_crux/status", json=crux_status, status_code=200)
    response = client.get("/_dev/health")
    assert response.json() == {
        "service": "octopoes",
        "healthy": True,
        "version": __version__,
        "additional": None,
        "results": [
            {
                "healthy": True,
                "service": "xtdb",
                "version": "21.05-1.17.0-beta",
                "additional": crux_status,
                "results": [],
            },
        ],
    }
    assert response.status_code == 200


def test_health_no_xtdb_connection(requests_mock, patch_pika):
    requests_mock.real_http = True
    requests_mock.get("http://crux:3000/_crux/status", exc=requests.exceptions.ConnectTimeout)
    response = client.get("/_dev/health")
    assert response.json() == {
        "service": "octopoes",
        "healthy": False,
        "version": __version__,
        "additional": None,
        "results": [
            {
                "healthy": False,
                "service": "xtdb",
                "version": None,
                "additional": "Cannot connect to XTDB at. Service possibly down",
                "results": [],
            },
        ],
    }
    assert response.status_code == 200


def test_openapi():
    response = client.get("/openapi.json")
    assert response.status_code == 200


def test_get_scan_profiles(requests_mock, patch_pika):
    requests_mock.real_http = True
    scan_profile = {
        "type": "ScanProfile",
        "level": 0,
        "reference": "Hostname|internet|mispo.es",
        "scan_profile_type": "empty",
        "xt/id": "ScanProfile|DNSZone|internet|mispo.es",
    }
    requests_mock.post(
        "http://crux:3000/_crux/query",
        json=[[scan_profile]],
        status_code=200,
    )
    response = client.get("/_dev/scan_profiles")
    assert response.status_code == 200
    assert response.json() == [{"level": 0, "reference": "Hostname|internet|mispo.es", "scan_profile_type": "empty"}]


def test_create_node():
    res = client.post("/_dev/node")
    assert res.status_code == 501
    assert res.json() == {"detail": "XTDB multinode is not set up for Octopoes."}


def test_delete_node():
    res = client.delete("/_dev/node")
    assert res.status_code == 501
    assert res.json() == {"detail": "XTDB multinode is not set up for Octopoes."}


def test_create_node_multinode(requests_mock, xtdbtype_multinode):
    requests_mock.real_http = True
    requests_mock.post(
        "http://crux:3000/_xtdb/create-node",
        json={"created": "true"},
        status_code=200,
    )
    response = client.post("/_dev/node")
    assert response.status_code == 200


def test_delete_node_multinode(requests_mock, xtdbtype_multinode):
    requests_mock.real_http = True
    requests_mock.post(
        "http://crux:3000/_xtdb/delete-node",
        json={"deleted": "true"},
        status_code=200,
    )
    response = client.delete("/_dev/node")
    assert response.status_code == 200


def test_count_findings_by_severity(requests_mock, patch_pika):
    requests_mock.real_http = True
    xt_response = [
        [
            {
                "object_type": "KATFindingType",
                "KATFindingType/risk_severity": "medium",
                "KATFindingType/id": "KAT-NO-DKIM",
                "KATFindingType/description": "This hostname does not support a DKIM record.",
                "KATFindingType/primary_key": "KATFindingType|KAT-NO-DKIM",
                "KATFindingType/risk_score": 6.9,
                "xt/id": "KATFindingType|KAT-NO-DKIM",
            },
            1,
        ]
    ]

    requests_mock.post(
        "http://crux:3000/_crux/query",
        json=xt_response,
        status_code=200,
    )
    response = client.get("/_dev/findings/count_by_severity")
    assert response.status_code == 200
    assert response.json() == {
        "critical": 0,
        "high": 0,
        "medium": 1,
        "low": 0,
        "recommendation": 0,
        "pending": 0,
        "unknown": 0,
    }
