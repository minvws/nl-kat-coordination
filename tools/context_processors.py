from django.conf import settings


def languages(request):
    context = {"languages": [code for code, _ in settings.LANGUAGES]}
    return context
