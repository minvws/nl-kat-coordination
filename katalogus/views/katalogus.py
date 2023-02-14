from typing import Any, Dict
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, FormView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator
from account.mixins import OrganizationView
from katalogus.client import get_katalogus
from katalogus.forms import KATalogusFilter


@class_view_decorator(otp_required)
class KATalogusView(ListView, OrganizationView, FormView):
    """View of all plugins in KAT-alogus"""

    template_name = "katalogus.html"
    form_class = KATalogusFilter

    def get_initial(self) -> Dict[str, Any]:
        initial = super().get_initial()

        initial["sorting_options"] = self.request.GET.get("sorting_options")
        initial["filter_options"] = self.request.GET.get("filter_options")

        return initial

    def get(self, request, *args, **kwargs):
        katalogus_client = get_katalogus(self.organization.code)
        self.all_plugins = katalogus_client.get_all_plugins()
        self.set_katalogus_view(kwargs)
        return super().get(request, *args, **kwargs)

    def set_katalogus_view(self, kwargs):
        self.view = ""
        if "view" in kwargs:
            self.view = kwargs["view"]

    def get_all_boefjes(self):
        return [plugin for plugin in self.all_plugins if plugin["type"] == "boefje"]

    def get_all_normalizers(self):
        return [plugin for plugin in self.all_plugins if plugin["type"] == "normalizer"]

    def get_queryset(self):
        queryset = self.get_all_boefjes()
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
            return [plugin for plugin in queryset if plugin["enabled"]]
        if filter_options == "disabled":
            return [plugin for plugin in queryset if not plugin["enabled"]]

    def sort_queryset(self, queryset, sort_options):
        if sort_options == "a-z":
            return queryset
        if sort_options == "z-a":
            return reversed(queryset)
        if sort_options == "enabled-disabled":
            return sorted(queryset, key=lambda item: not item["enabled"])
        if sort_options == "disabled-enabled":
            return sorted(queryset, key=lambda item: item["enabled"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {
                "url": reverse("katalogus", kwargs={"organization_code": self.organization.code}),
                "text": _("KAT-alogus"),
            },
        ]
        context["view"] = self.view
        return context
