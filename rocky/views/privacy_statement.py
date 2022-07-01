from django.views.generic import TemplateView
from django.shortcuts import reverse
from django.utils.translation import gettext_lazy as _


class PrivacyStatementView(TemplateView):
    template_name = "legal/privacy_statement.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["breadcrumbs"] = [
            {"url": reverse("privacy_statement"), "text": _("Privacy Statement")},
        ]

        return context
