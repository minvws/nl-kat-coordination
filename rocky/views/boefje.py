from datetime import datetime, timezone
from logging import getLogger
from pickle import DICT
from typing import Any, Dict, List, Tuple
from enum import Enum

from django.contrib import messages
from django.http import Http404, FileResponse, QueryDict
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView
from django_otp.decorators import otp_required
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference, OOI, DeclaredScanProfile
from two_factor.views.utils import class_view_decorator

from rocky.boefjes import BoefjeTask, run_boefje
from rocky.katalogus import (
    Boefje,
    KATalogusBreadcrumbsMixin,
    get_katalogus,
    KATalogusClientV1,
)
from rocky.views import OctopoesMixin
from tools.forms import SelectOOIForm
from tools.models import Organization
from tools.view_helpers import Breadcrumb, PageActionMixin

logger = getLogger(__name__)


class BoefjeMixin(OctopoesMixin):
    """
    When a user wants to scan one or multiple OOI's, this mixin provides the methods to construct the boefjes for the OOI's and run them.
    """

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.api_connector = self.get_api_connector()

    def run_boefje_for_oois(
        self,
        boefje: Boefje,
        oois: List[OOI],
        organization: Organization,
        api_connector: OctopoesAPIConnector,
    ) -> Tuple[List[BoefjeTask], bool]:

        for ooi in oois:
            if ooi.scan_profile.level < boefje.scan_level:
                api_connector.save_scan_profile(
                    DeclaredScanProfile(
                        reference=ooi.reference,
                        level=boefje.scan_level,
                    ),
                    datetime.now(timezone.utc),
                )

        boefje_tasks = [
            BoefjeTask(
                boefje=boefje,
                input_ooi=ooi.reference,
                organization=organization.code,
            )
            for ooi in oois
        ]

        if not boefje_tasks:
            return boefje_tasks, False

        for boefje_task in boefje_tasks:
            run_boefje(boefje_task, organization)

        return boefje_tasks, True

    def boefje_enable(self, view_args) -> None:
        boefje_id = view_args.get("boefje_id")
        organization = self.request.active_organization
        get_katalogus(organization.code).enable_boefje(boefje_id)
        messages.add_message(
            self.request,
            messages.INFO,
            _("Boefje '{boefje_id}' enabled for '{organization_name}'.").format(
                boefje_id=boefje_id, organization_name=organization.name
            ),
        )

    def boefje_disable(self, view_args) -> None:
        boefje_id = view_args.get("boefje_id")
        organization = self.request.active_organization
        get_katalogus(organization.code).disable_boefje(boefje_id)
        messages.add_message(
            self.request,
            messages.INFO,
            _("Boefje '{boefje_id}' disabled for '{organization_name}'.").format(
                boefje_id=boefje_id, organization_name=organization.name
            ),
        )

    def scan(self, view_args) -> None:
        if "ooi" not in view_args:
            return

        if "boefje_id" not in view_args:
            return

        boefje_id = view_args.get("boefje_id")
        boefje = self.get_boefje(boefje_id)

        if not boefje.enabled:
            messages.add_message(
                self.request,
                messages.WARNING,
                _("Trying to run disabled boefje '{boefje_id}'.").format(
                    boefje_id=boefje_id
                ),
            )
            return

        ooi_ids = view_args.getlist("ooi")
        oois = [self.get_single_ooi(ooi_id) for ooi_id in ooi_ids]

        ran_boefjes, success = self.run_boefje_for_oois(
            boefje, oois, self.request.active_organization, self.api_connector
        )
        if not success:
            return
        success_message = _(
            "Your scan is running successfully in the background. \n Results will be added to the object list when they are in. It may take some time, a refresh of the page may be needed to show the results."
        )
        messages.add_message(self.request, messages.SUCCESS, success_message)
        return


@class_view_decorator(otp_required)
class BoefjeDetailView(
    KATalogusBreadcrumbsMixin, BoefjeMixin, PageActionMixin, TemplateView
):
    class PageActions(Enum):
        BOEFJE_DISABLE = "boefje_disable"
        BOEFJE_ENABLE = "boefje_enable"
        START_SCAN = "scan"

    template_name = "boefje_detail.html"
    boefje: Boefje = None

    def get_boefje(self, boefje_id: str) -> Boefje:
        try:
            return get_katalogus(self.request.active_organization.code).get_boefje(
                boefje_id
            )
        except:
            raise Http404("Boefje not found")

    def get_page_action_args(self, page_action) -> QueryDict:
        if page_action == self.PageActions.START_SCAN.value:
            args = self.request.POST.copy()
            args["boefje_id"] = self.kwargs["id"]
            return args
        return super().get_page_action_args(page_action)

    def get(self, request, *args, **kwargs):
        self.boefje = self.get_boefje(kwargs["id"])
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if "action" not in self.request.POST:
            return self.get(request, *args, **kwargs)

        action = self.request.POST.get("action")
        self.handle_page_action(action)

        action_enum = self.PageActions(action)

        if action_enum == self.PageActions.START_SCAN:
            return redirect("task_list")

        return self.get(request, *args, **kwargs)

    def build_breadcrumbs(self) -> List[Breadcrumb]:
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append(
            {
                "url": reverse("katalogus_detail", kwargs={"id": self.boefje.id}),
                "text": self.boefje.name,
            }
        )
        return breadcrumbs

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        connector = self.get_api_connector()

        ooi_reference = (
            Reference.from_str(self.request.GET["ooi_id"])
            if "ooi_id" in self.request.GET
            else None
        )
        ooi = connector.get(ooi_reference) if ooi_reference else None

        context = super().get_context_data(**kwargs)
        context["checkbox_group_table_form"] = (
            SelectOOIForm(self.boefje, connector, ooi),
        )
        context["boefje"] = self.boefje
        context["description"] = get_katalogus(
            self.request.active_organization.code
        ).get_description(self.boefje.id)
        context["boefje_disabled"] = not self.boefje.enabled

        return context


@class_view_decorator(otp_required)
class BoefjeCoverView(View):
    def get(self, request, boefje_id: str):
        return FileResponse(
            get_katalogus(self.request.active_organization.code).get_cover(boefje_id)
        )
