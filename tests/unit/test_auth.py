from datetime import datetime, timezone

from fastapi.testclient import TestClient

from bytes.auth import authenticate_token
from tests.loading import load_stub


def test_login_get_token(test_client: TestClient) -> None:
    request = load_stub("login-request.json")

    response = test_client.post("/token", data=request)

    assert response.status_code == 200

    data = response.json()
    assert data["token_type"] == "bearer"
    assert authenticate_token(data["access_token"]) == "test"
    assert datetime.fromisoformat(data["expires_at"]) > datetime.now(timezone.utc)


def test_login_get_token_not_authorized(test_client: TestClient) -> None:
    request = load_stub("login-request.json")
    request["username"] = "nivlac"

    response = test_client.post("/token", data=request)
    assert response.status_code == 401
