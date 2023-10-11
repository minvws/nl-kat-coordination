from typing import Any, Dict

from account.mixins import OrganizationView
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, ListView, TemplateView

from katalogus.client import get_katalogus
from katalogus.forms import KATalogusFilter


class BaseKATalogusView(OrganizationView, ListView, FormView):
    form_class = KATalogusFilter

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.katalogus_client = get_katalogus(self.organization.code)

    def get_initial(self) -> Dict[str, Any]:
        initial = super().get_initial()
        initial["sorting_options"] = self.request.GET.get("sorting_options", "a-z")
        initial["filter_options"] = self.request.GET.get("filter_options", "all")
        return initial

    def filter_katalogus(self, queryset):
        if "filter_options" in self.request.GET:
            filter_options = self.request.GET.get("filter_options")
            queryset = self.filter_queryset(queryset, filter_options)
        if "sorting_options" in self.request.GET:
            sorting_options = self.request.GET["sorting_options"]
            queryset = self.sort_queryset(queryset, sorting_options)
        return queryset

    def filter_queryset(self, queryset, filter_options):
        if filter_options == "all":
            return queryset
        if filter_options == "enabled":
            return [plugin for plugin in queryset if plugin.enabled]
        if filter_options == "disabled":
            return [plugin for plugin in queryset if not plugin.enabled]

    def sort_queryset(self, queryset, sort_options):
        if sort_options == "a-z":
            return queryset
        if sort_options == "z-a":
            return queryset[::-1]
        if sort_options == "enabled-disabled":
            return sorted(queryset, key=lambda item: not item.enabled)
        if sort_options == "disabled-enabled":
            return sorted(queryset, key=lambda item: item.enabled)

    def sort_alphabetic_ascending(self, queryset):
        return sorted(queryset, key=lambda item: item.name.lower())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view_type"] = self.kwargs.get("view_type", "grid")
        context["url_name"] = self.request.resolver_match.url_name
        context["breadcrumbs"] = [
            {
                "url": reverse("katalogus", kwargs={"organization_code": self.organization.code}),
                "text": _("KAT-alogus"),
            },
        ]
        return context


class KATalogusView(BaseKATalogusView):
    """View of all plugins in KAT-alogus"""

    template_name = "katalogus.html"

    def get_queryset(self):
        queryset = self.sort_alphabetic_ascending(self.katalogus_client.get_plugins())
        return self.filter_katalogus(queryset)


class BoefjeListView(BaseKATalogusView):
    """Showing only Boefjes in KAT-alogus"""

    template_name = "boefjes.html"

    def get_queryset(self):
        queryset = self.sort_alphabetic_ascending(self.katalogus_client.get_boefjes())
        return self.filter_katalogus(queryset)


class NormalizerListView(BaseKATalogusView):
    """Showing only Normalizers in KAT-alogus"""

    template_name = "normalizers.html"

    def get_queryset(self):
        queryset = self.sort_alphabetic_ascending(self.katalogus_client.get_normalizers())
        return self.filter_katalogus(queryset)


class AboutPluginsView(OrganizationView, TemplateView):
    template_name = "about_plugins.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view_type"] = self.kwargs.get("view_type", "grid")
        context["breadcrumbs"] = [
            {
                "url": reverse("katalogus", kwargs={"organization_code": self.organization.code}),
                "text": _("KAT-alogus"),
            },
        ]
        return context
