from django.urls import reverse
from django.urls.base import reverse_lazy
from django.contrib.auth import views as auth_views


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    """
    Password reset notification view
    """

    template_name = "account/password_reset_done.html"
    success_url = reverse_lazy("login")
