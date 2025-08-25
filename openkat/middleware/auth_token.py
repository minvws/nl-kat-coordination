import structlog
from django.http import HttpResponseForbidden
from knox.auth import TokenAuthentication
from rest_framework.exceptions import APIException


def MediaAuthTokenMiddleware(get_response):
    """Allow TokenAuthentication for media files as well to provide plugins access to files"""

    def middleware(request):
        if (
            not request.user.is_authenticated
            and "authorization" in request.headers
            and request.path.startswith("/media")
        ):
            authenticator = TokenAuthentication()
            try:
                user_and_token = authenticator.authenticate(request)
            except APIException:
                return HttpResponseForbidden("Invalid token\n")
            else:
                if user_and_token:
                    request.user = user_and_token[0]
                    structlog.contextvars.bind_contextvars(auth_method="token")

        return get_response(request)

    return middleware
