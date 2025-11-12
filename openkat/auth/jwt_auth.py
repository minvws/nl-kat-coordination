from datetime import datetime, timedelta

import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from jwt import PyJWTError
from rest_framework.authentication import TokenAuthentication


class JWTTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        try:
            return AnonymousUser(), jwt.decode(
                key, settings.JWT_KEY, algorithms=[settings.JWT_ALGORITHM], options={"require": ["exp", "iat"]}
            )
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
