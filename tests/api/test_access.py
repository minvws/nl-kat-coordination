from datetime import datetime, timedelta

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives._serialization import Encoding, NoEncryption, PrivateFormat
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth.models import Permission
from django.db.models import Q

from openkat.auth.jwt_auth import JWTTokenAuthentication
from tests.conftest import JSONAPIClient


def test_api_access(organization):
    client = JSONAPIClient(raise_request_exception=True)
    token = JWTTokenAuthentication.generate([])
    client.credentials(HTTP_AUTHORIZATION="Token " + token)

    response = client.get("/api/v1/file/")
    assert response.status_code == 403
    assert response.json() == {
        "errors": [
            {"attr": None, "code": "permission_denied", "detail": "You do not have permission to perform this action."}
        ],
        "type": "client_error",
    }

    token = JWTTokenAuthentication.generate(["files.view_file", "files.add_file"])
    client.credentials(HTTP_AUTHORIZATION="Token " + token)

    response = client.get("/api/v1/file/")
    assert response.status_code == 200

    response = client.get("/api/v1/objects/network/")
    assert response.status_code == 403

    perms = [
        f"{ct}.{name}"
        for ct, name in Permission.objects.filter(
            ~Q(codename__contains="organization"), Q(content_type__app_label="objects")
        ).values_list("content_type__app_label", "codename")
    ]

    token = JWTTokenAuthentication.generate(["files.view_file", "files.add_file"] + perms)
    client.credentials(HTTP_AUTHORIZATION="Token " + token)

    response = client.get("/api/v1/objects/network/")
    assert response.status_code == 200

    now = datetime.now()
    token_data = {
        "permissions": ["files.view_file", "files.add_file"],
        "iat": now.timestamp(),
        "exp": (now + timedelta(minutes=15)).timestamp(),
    }
    wrong_private_key = rsa.generate_private_key(65537, 4096, default_backend()).private_bytes(
        encoding=Encoding.PEM, format=PrivateFormat.PKCS8, encryption_algorithm=NoEncryption()
    )
    token = jwt.encode(token_data, wrong_private_key, algorithm="RS256")
    client.credentials(HTTP_AUTHORIZATION="Token " + token)
    response = client.get("/api/v1/file/")

    assert response.status_code == 401
    assert response.json() == {
        "errors": [{"attr": None, "code": "authentication_failed", "detail": "Invalid token."}],
        "type": "client_error",
    }
