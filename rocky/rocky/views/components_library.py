from django.shortcuts import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView


class ComponentsLibraryView(TemplateView):
    template_name = "organizations/components_library.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["breadcrumbs"] = [
            {"url": reverse("components_library"), "text": _("Components Library")},
        ]

        return context
