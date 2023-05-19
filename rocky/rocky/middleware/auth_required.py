from django.shortcuts import redirect
from django.urls.base import reverse


def AuthRequiredMiddleware(get_response):
    def middleware(request):
        login_path = reverse("login")
        excluded = [
            "/",
            login_path,
            reverse("recover_email"),
            reverse("password_reset"),
            reverse("landing_page"),
            reverse("set_language"),
            reverse("privacy_statement"),
        ]
        excluded_prefix = [
            # There won't be a request.user if auth tokens are used, but
            # Django REST framework will make sure that there is an
            # authenticated user without DEFAULT_PERMISSION_CLASSES setting
            # in settings.py.
            "/api/",
            "/account/reset/",
        ]

        if not request.user.is_authenticated and (
            # check if path is not in excluded list
            request.path not in excluded
            # check if path starts with anything in excluded_prefix
            and not any([request.path.startswith(prefix) for prefix in excluded_prefix])
        ):
            return redirect(login_path)

        return get_response(request)

    return middleware
