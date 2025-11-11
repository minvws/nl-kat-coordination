from openkat.middleware.jwt_auth import JWTTokenAuthentication
from tests.conftest import JSONAPIClient


def test_files_api_access(organization):
    client = JSONAPIClient(raise_request_exception=True)
    token = JWTTokenAuthentication.generate([])
    client.credentials(HTTP_AUTHORIZATION="Token " + token)

    response = client.get("/api/v1/file/")
    assert response.status_code == 401

    token = JWTTokenAuthentication.generate(["files.view_file", "files.add_file", "objects.*"])
    client.credentials(HTTP_AUTHORIZATION="Token " + token)

    response = client.get("/api/v1/file/")
    assert response.status_code == 200
