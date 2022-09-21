from datetime import datetime, timezone
from enum import Enum
from logging import getLogger
from typing import Any, Dict, List, Type, Optional
from uuid import uuid4
from django.views.generic.edit import FormView
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
from octopoes.models.types import type_by_name
from requests import HTTPError
from two_factor.views.utils import class_view_decorator

from katalogus.client import (
    KATalogusBreadcrumbsMixin,
    get_katalogus,
)

from rocky.scheduler import QueuePrioritizedItem, BoefjeTask, Boefje, client
from rocky.views import OctopoesMixin
from rocky.views.ooi_view import BaseOOIFormView
from tools.forms import SelectOOIForm, SelectOOIFilterForm
from tools.models import Organization
from tools.view_helpers import Breadcrumb, PageActionMixin, existing_ooi_type

logger = getLogger(__name__)


class BoefjeMixin(OctopoesMixin):
    """
    When a user wants to scan one or multiple OOI's,
    this mixin provides the methods to construct the boefjes for the OOI's and run them.
    """

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.api_connector = self.get_api_connector()

    def run_boefje(
        self, katalogus_boefje: Boefje, ooi: OOI, organization: Organization
    ) -> None:

        boefje_queue_name = f"boefje-{organization.code}"

        boefje = Boefje(
            id=katalogus_boefje.id,
            name=katalogus_boefje.name,
            description=katalogus_boefje.description,
            repository_id=katalogus_boefje.repository_id,
            version=None,
            scan_level=katalogus_boefje.scan_level.value,
            consumes={
                ooi_class.get_ooi_type() for ooi_class in katalogus_boefje.consumes
            },
            produces={
                ooi_class.get_ooi_type() for ooi_class in katalogus_boefje.produces
            },
        )

        boefje_task = BoefjeTask(
            id=uuid4().hex,
            boefje=boefje,
            input_ooi=ooi.reference,
            organization=organization.code,
        )

        item = QueuePrioritizedItem(priority=1, item=boefje_task)
        client.push_task(boefje_queue_name, item)

    def run_boefje_for_oois(
        self,
        boefje: Boefje,
        oois: List[OOI],
        organization: Organization,
        api_connector: OctopoesAPIConnector,
    ) -> None:

        for ooi in oois:
            if ooi.scan_profile.level < boefje.scan_level:
                api_connector.save_scan_profile(
                    DeclaredScanProfile(
                        reference=ooi.reference,
                        level=boefje.scan_level,
                    ),
                    datetime.now(timezone.utc),
                )
            self.run_boefje(boefje, ooi, organization)

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

        try:
            self.run_boefje_for_oois(
                boefje, oois, self.request.active_organization, self.api_connector
            )
        except HTTPError:
            return

        success_message = _(
            "Your scan is running successfully in the background. \n "
            "Results will be added to the object list when they are in. "
            "It may take some time, a refresh of the page may be needed to show the results."
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
        FILTER_OBJECTS = "filter_objects"

    template_name = "boefje_detail.html"
    boefje: Optional[Boefje] = None

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
        context = super().get_context_data(**kwargs)

        filter_form = SelectOOIFilterForm(self.request.GET)

        # fetch ooi or oois
        oois = []
        connector = self.get_api_connector()

        if "ooi_id" in self.request.GET:
            oois.append(connector.get(Reference.from_str(self.request.GET["ooi_id"])))
        else:
            # TODO: Instead of this arbitrary limit add pagination.
            oois = connector.list(self.boefje.consumes, limit=9999)

        has_consumable_oois = False
        if len(oois) > 0:
            has_consumable_oois = True

        # filter by scan-level
        if filter_form.is_valid() and not filter_form.cleaned_data["show_all"]:
            oois = [
                ooi for ooi in oois if ooi.scan_profile.level >= self.boefje.scan_level
            ]

        context["select_ooi_filter_form"] = filter_form
        context["select_oois_form"] = SelectOOIForm(oois)
        context["has_consumable_oois"] = has_consumable_oois
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


@class_view_decorator(otp_required)
class BoefjeConsumableObjectType(TemplateView):
    template_name = "oois/ooi_add_type_select.html"
    boefje: Boefje = None

    def get(self, request, *args, **kwargs):
        self.boefje = self.get_boefje(kwargs["id"])

        if "add_ooi_type" in request.GET and existing_ooi_type(
            request.GET["add_ooi_type"]
        ):
            return redirect(
                reverse(
                    "boefje_add_consumable_object",
                    kwargs={
                        "id": self.boefje.id,
                        "add_ooi_type": request.GET["add_ooi_type"],
                    },
                )
            )

        return super().get(request, *args, **kwargs)

    def get_boefje(self, boefje_id: str) -> Boefje:
        try:
            return get_katalogus(self.request.active_organization.code).get_boefje(
                boefje_id
            )
        except:
            raise Http404("Boefje not found")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {
                "url": reverse("katalogus_detail", args=[self.boefje.id]),
                "text": self.boefje.name,
            },
            {"url": reverse("ooi_add_type_select"), "text": _("Add consumable object")},
        ]
        context["ooi_types"] = [
            {"value": ooi_type.get_ooi_type(), "text": ooi_type.get_ooi_type()}
            for ooi_type in self.boefje.consumes
        ]
        return context


@class_view_decorator(otp_required)
class BoefjeConsumableObjectAddView(BaseOOIFormView):
    template_name = "oois/ooi_add.html"
    boefje: Boefje = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.ooi_class = self.get_ooi_class()
        self.initial = request.GET
        self.boefje = self.get_boefje(kwargs["id"])

    def get_boefje(self, boefje_id: str) -> Boefje:
        try:
            return get_katalogus(self.request.active_organization.code).get_boefje(
                boefje_id
            )
        except:
            raise Http404("Boefje not found")

    def get_ooi_class(self) -> Type[OOI]:
        try:
            return type_by_name(self.kwargs["add_ooi_type"])
        except KeyError:
            raise Http404("OOI not found")

    def get_success_url(self, ooi) -> str:
        return reverse("katalogus_detail", args=[self.boefje.id])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["type"] = self.ooi_class.get_ooi_type()
        context["breadcrumbs"] = [
            {
                "url": reverse("katalogus_detail", args=[self.boefje.id]),
                "text": self.boefje.name,
            },
            {"url": reverse("ooi_add_type_select"), "text": _("Add consumable object")},
            {
                "url": reverse(
                    "ooi_add", kwargs={"ooi_type": self.ooi_class.get_ooi_type()}
                ),
                "text": _("Add %(ooi_type)s")
                % {"ooi_type": self.ooi_class.get_ooi_type()},
            },
        ]

        return context
