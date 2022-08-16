from django.views.generic import TemplateView
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from rocky.settings import HELP_DESK_EMAIL


class RecoverEmailView(TemplateView):
    """
    Handler for email recovery.
    """

    template_name = "recover_email.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["help_desk_email"] = HELP_DESK_EMAIL
        context["breadcrumbs"] = [
            {
                "url": reverse("login"),
                "text": _("Login"),
            },
            {
                "url": reverse("recover_email"),
                "text": _("Recover email address"),
            },
        ]
        return context
