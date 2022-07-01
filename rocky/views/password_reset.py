from django.contrib.auth import views as auth_views
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.contrib import messages
from tools.forms import PasswordResetForm


class PasswordResetView(auth_views.PasswordResetView):
    """
    Handler to reset password with user's email address
    """

    template_name = "account/password_reset.html"
    email_template_name = "account/password_reset_email.html"
    subject_template_name = "account/password_reset_subject.txt"
    form_class = PasswordResetForm
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
        success_message = "We've emailed you instructions for setting your password. You should receive the email shortly!"
        messages.add_message(self.request, messages.SUCCESS, success_message)
