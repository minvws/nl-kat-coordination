from rocky.settings import MIAUW_API_ENABLED, LANGUAGES


def miauw_api(request):
    return {"miauw_api_enabled": MIAUW_API_ENABLED}


def languages(request):
    context = {"languages": [code for code, _ in LANGUAGES]}
    return context
