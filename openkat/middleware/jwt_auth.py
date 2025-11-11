from datetime import datetime, timedelta

import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.urls import Resolver404, resolve
from jwt import PyJWTError
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from openkat.permissions import KATModelPermissions


class JWTTokenAuthentication(TokenAuthentication):
    def authenticate(self, request):
        out = super().authenticate(request)

        if not out:
            return out

        try:
            match = resolve(request.path)
        except Resolver404:
            match = None

        if match:
            user, token_data = out
            kat_model_perms = KATModelPermissions()
            perms = kat_model_perms.get_required_permissions(request.method, match.func.cls.queryset.model)

            for perm in perms:
                if perm not in (token_data.get("permissions", []) or []):
                    raise AuthenticationFailed(f"Insufficient permissions in JWT token, missing at least: {perm}")

            return user, token_data

    def authenticate_credentials(self, key):
        try:
            return AnonymousUser(), jwt.decode(key, settings.JWT_KEY, algorithms=[settings.JWT_ALGORITHM])
        except PyJWTError:
            return None

    @classmethod
    def generate(cls, permissions: list[str] | None = None, timeout: int = settings.PLUGIN_TIMEOUT) -> str:
        now = datetime.now()
        token_data = {
            "permissions": permissions,
            "iat": now.timestamp(),
            "exp": (now + timedelta(minutes=timeout)).timestamp(),
        }
        return jwt.encode(token_data, settings.JWT_KEY, algorithm=settings.JWT_ALGORITHM)
