from rocky.settings import LANGUAGES


def languages(request):
    context = {"languages": [code for code, _ in LANGUAGES]}
    return context
