from django.conf import settings
from django.contrib.auth.middleware import RemoteUserMiddleware as BaseRemoteUserMiddleware


class RemoteUserMiddleware(BaseRemoteUserMiddleware):
    header = settings.REMOTE_USER_HEADER
