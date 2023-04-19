from account.models import KATUser
from django.conf import settings


def languages(request):
    context = {"languages": [code for code, _ in settings.LANGUAGES]}
    return context


def organizations_including_blocked(request):
    context = {}
    if isinstance(request.user, KATUser):
        context["organizations_including_blocked"] = request.user.organizations_including_blocked
    return context
