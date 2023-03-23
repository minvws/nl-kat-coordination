from logging import getLogger
from typing import List, Optional
from uuid import uuid4

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from requests import RequestException, HTTPError
from rest_framework.status import HTTP_404_NOT_FOUND

from account.mixins import OrganizationView
from katalogus.client import get_katalogus, Plugin
from octopoes.models import OOI
from rocky.exceptions import IndemnificationNotPresentException, ClearanceLevelTooLowException
from rocky.scheduler import Boefje, BoefjeTask, QueuePrioritizedItem, client
from rocky.views.mixins import OctopoesView

logger = getLogger(__name__)


class SinglePluginView(OrganizationView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.katalogus_client = None
        self.plugin_schema = None
        self.plugin = None

    def setup(self, request, *args, **kwargs):
        """
        Prepare organization info and KAT-alogus API client.
        """
        super().setup(request, *args, **kwargs)
        self.katalogus_client = get_katalogus(self.organization.code)
        plugin_id = kwargs.get("plugin_id")

        try:
            self.plugin = self.katalogus_client.get_plugin(plugin_id)
            self.plugin_schema = self.katalogus_client.get_plugin_schema(plugin_id)
        except HTTPError as e:
            if e.response.status_code == HTTP_404_NOT_FOUND:
                raise Http404("Plugin {} not found.".format(plugin_id))

            raise
        except RequestException:
            messages.add_message(
                self.request,
                messages.ERROR,
                _("Getting information for plugin {} failed. Please check the KATalogus logs.").format(plugin_id),
            )

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_anonymous:
            return redirect(reverse("login"))

        if not self.plugin:
            return redirect(reverse("katalogus", kwargs={"organization_code": self.organization.code}))

        return super().dispatch(request, *args, **kwargs)

    def is_required_field(self, field: str) -> bool:
        return self.plugin_schema and field in self.plugin_schema.get("required", [])

    def is_valid_setting(self, setting_name: str) -> bool:
        return self.plugin_schema and setting_name in self.plugin_schema.get("properties", [])


class SingleSettingView(SinglePluginView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setting_name = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        if not self.is_valid_setting(kwargs.get("setting_name")):
            raise Http404("Setting {} is not valid for this plugin.".format(kwargs.get("setting_name")))

        self.setting_name = kwargs.get("setting_name")


class BoefjeMixin(OctopoesView):
    """
    When a user wants to scan one or multiple OOI's,
    this mixin provides the methods to construct the boefjes for the OOI's and run them.
    """

    def run_boefje(self, katalogus_boefje: Plugin, ooi: Optional[OOI]) -> None:
        boefje_queue_name = f"boefje-{self.organization.code}"

        boefje = Boefje(
            id=katalogus_boefje.id,
            name=katalogus_boefje.name,
            description=katalogus_boefje.description,
            repository_id=katalogus_boefje.repository_id,
            version=None,
            scan_level=katalogus_boefje.scan_level.value,
            consumes={ooi_class.get_ooi_type() for ooi_class in katalogus_boefje.consumes},
            produces={ooi_class.get_ooi_type() for ooi_class in katalogus_boefje.produces},
        )

        boefje_task = BoefjeTask(
            id=uuid4().hex,
            boefje=boefje,
            input_ooi=ooi.reference if ooi else None,
            organization=self.organization.code,
        )

        item = QueuePrioritizedItem(id=boefje_task.id, priority=1, data=boefje_task)
        logger.info("Item: %s", item.json())
        client.push_task(boefje_queue_name, item)

    def run_boefje_for_oois(
        self,
        boefje: Plugin,
        oois: List[OOI],
    ) -> None:
        if not oois and not boefje.consumes:
            self.run_boefje(boefje, None)

        for ooi in oois:
            if ooi.scan_profile.level < boefje.scan_level:
                try:
                    self.raise_clearance_level(ooi.reference, boefje.scan_level)
                except (IndemnificationNotPresentException, ClearanceLevelTooLowException):
                    continue
            self.run_boefje(boefje, ooi)
