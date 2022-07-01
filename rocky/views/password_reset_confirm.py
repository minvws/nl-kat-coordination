from django.urls import reverse
from django.urls.base import reverse_lazy
from django.contrib.auth import views as auth_views
from django.contrib import messages
from tools.forms import SetPasswordForm


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """
    Views a form so user can enter a new password and password confirmation.
    """

    template_name = "account/password_reset_confirm.html"
    form_class = SetPasswordForm
    success_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = (
            [
                {"url": reverse("login"), "text": "Login"},
                {"url": reverse("password_reset"), "text": "Reset password"},
            ],
        )
        context["form_name"] = "recovery-flow"
        return context

    def form_valid(self, form):
        form_valid = super().form_valid(form)
        self.add_success_notification()
        return form_valid

    def add_success_notification(self):
        success_message = "Password reset is succesfully done."
        messages.add_message(self.request, messages.SUCCESS, success_message)
