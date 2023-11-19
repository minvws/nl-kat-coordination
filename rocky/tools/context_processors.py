from account.models import KATUser
from django.conf import settings

from rocky.version import __version__


def feature_flags(request):
    context = {}
    for name in dir(settings):
        if name.startswith("FEATURE_"):
            context[name] = getattr(settings, name)
    return context


def languages(request):
    context = {"languages": [code for code, _ in settings.LANGUAGES]}
    return context


def organizations_including_blocked(request):
    context = {}
    if isinstance(request.user, KATUser):
        context["organizations_including_blocked"] = request.user.organizations_including_blocked
    return context


def rocky_version(request):
    context = {"rocky_version": __version__}
    return context
