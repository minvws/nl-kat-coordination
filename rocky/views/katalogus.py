from enum import Enum
from operator import attrgetter
from typing import Any, Dict, List

from django.urls.base import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from rocky.views.boefje import BoefjeMixin
from katalogus.client import Boefje, get_katalogus
from tools.view_helpers import BreadcrumbsMixin, PageActionMixin

BOEFJE_STATUSES = [
    {"value": "enabled", "label": _("Enabled")},
    {"value": "disabled", "label": _("Disabled")},
]

SORTING_OPTIONS = [
    {"value": "a-z", "label": _("A-Z")},
    {"value": "z-a", "label": _("Z-A")},
    {"value": "enabled-disabled", "label": _("Enabled-Disabled")},
    {"value": "disabled-enabled", "label": _("Disabled-Enabled")},
]


class KATalogusBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [{"text": "KAT-alogus", "url": reverse_lazy("katalogus")}]


@class_view_decorator(otp_required)
class KATalogusListView(
    PageActionMixin, KATalogusBreadcrumbsMixin, BoefjeMixin, TemplateView
):
    class PageActions(Enum):
        BOEFJE_DISABLE = "boefje_disable"
        BOEFJE_ENABLE = "boefje_enable"

    filters_active = []
    sorting_active = []

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        self.filters_active = self.get_filters_active()
        self.sorting_active = self.get_sorting_active()

    def post(self, request, *args, **kwargs):
        if "action" not in self.request.POST:
            return self.get(request, *args, **kwargs)

        self.handle_page_action(self.request.POST.get("action"))

        return self.get(request, *args, **kwargs)

    def is_allowed_page_action(self, page_action: str) -> bool:
        if not self.request.user.has_perm("tools.can_enable_disable_boefje"):
            return False

        return super().is_allowed_page_action(page_action)

    def get_template_names(self) -> List[str]:
        if self.request.GET.get("view") == "list":
            return ["katalogus/list.html"]

        return ["katalogus/grid.html"]

    def get_filters_active(self) -> List[str]:
        return self.request.GET.getlist("boefje_status_filter")

    def get_sorting_active(self) -> str:
        return self.request.GET.get("katalogus_sorting", "")

    def get_checkbox_filters(self) -> List[Dict]:
        return [
            {
                "label": status["label"],
                "value": status["value"],
                "checked": not self.filters_active
                or status["value"] in self.filters_active,
            }
            for status in BOEFJE_STATUSES
        ]

    def get_sorting_options(self) -> List[Dict]:
        sorting_options = [
            {
                "label": sorting_option["label"],
                "value": sorting_option["value"],
                "checked": sorting_option["value"] in self.sorting_active,
            }
            for sorting_option in SORTING_OPTIONS
        ]

        if not self.sorting_active:
            for option in sorting_options:
                if option["value"] == "a-z":
                    option["checked"] = True

        return sorting_options

    def get_boefjes(self) -> List[Boefje]:
        boefjes = get_katalogus(self.request.active_organization.code).get_boefjes()

        if self.filters_active and "enabled" not in self.filters_active:
            boefjes = [boefje for boefje in boefjes if not boefje.enabled]

        if self.filters_active and "disabled" not in self.filters_active:
            boefjes = [boefje for boefje in boefjes if boefje.enabled]

        if self.sorting_active:
            if "z-a" in self.sorting_active:
                boefjes = sorted(boefjes, key=attrgetter("name"), reverse=True)
            if "a-z" in self.sorting_active:
                boefjes = sorted(boefjes, key=attrgetter("name"))
            if "enabled-disabled" in self.sorting_active:
                boefjes = sorted(boefjes, key=attrgetter("enabled"), reverse=True)
            if "disabled-enabled" in self.sorting_active:
                boefjes = sorted(boefjes, key=attrgetter("enabled"))

        return boefjes

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)

        context["checkbox_filters"] = self.get_checkbox_filters()
        context["radio_sorting"] = self.get_sorting_options()
        context["active_filters"] = self.filters_active
        context["active_sorting"] = self.sorting_active
        context["boefjes"] = self.get_boefjes()

        return context
