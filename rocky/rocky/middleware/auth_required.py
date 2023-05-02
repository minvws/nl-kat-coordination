from django.shortcuts import redirect
from django.urls.base import reverse


def AuthRequiredMiddleware(get_response):
    def middleware(request):
        login_path = reverse("login")
        email_recovery_path = reverse("recover_email")
        password_recovery_path = reverse("password_reset")
        home_path = reverse("landing_page")
        lang_path = reverse("set_language")
        privacy_statement = reverse("privacy_statement")

        if not request.user.is_authenticated and (
            not request.path.startswith("/account/reset/")
            # There won't be a request.user if auth tokens are used, but
            # Django REST framework will make sure that there is an
            # authenticated user with out DEFAULT_PERMISSION_CLASSES setting
            and not request.path.startswith("/api/")
            and request.path
            not in (
                "/",
                home_path,
                login_path,
                lang_path,
                email_recovery_path,
                password_recovery_path,
                privacy_statement,
            )
        ):
            return redirect(login_path)

        return get_response(request)

    return middleware
