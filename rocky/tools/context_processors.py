from django.conf import settings

from account.models import KATUser


def languages(request):
    context = {"languages": [code for code, _ in settings.LANGUAGES]}
    return context


def organizations_including_blocked(request):
    context = {}
    if isinstance(request.user, KATUser):
        context["organizations_including_blocked"] = [
            m.organization for m in request.user.members.select_related("organization")
        ]
    return context
