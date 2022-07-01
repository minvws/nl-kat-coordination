from django.contrib.auth import views as auth_views
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.contrib import messages
from django.core.mail import BadHeaderError


class PasswordResetCompleteView(auth_views.PasswordResetDoneView):
    """
    Password reset notification view
    """

    template_name = "account/password_reset_done.html"
    success_url = reverse_lazy("login")
