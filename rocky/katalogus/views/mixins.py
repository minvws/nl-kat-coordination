from logging import getLogger

from account.mixins import OrganizationView
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from httpx import HTTPError, HTTPStatusError
from rest_framework.status import HTTP_404_NOT_FOUND
from tools.view_helpers import schedule_task

from katalogus.client import Boefje as KATalogusBoefje
from katalogus.client import KATalogusClientV1, get_katalogus
from katalogus.client import Normalizer as KATalogusNormalizer
from octopoes.models import OOI
from rocky.scheduler import Boefje, BoefjeTask, Normalizer, NormalizerTask, PrioritizedItem, RawData
from rocky.views.mixins import OctopoesView

logger = getLogger(__name__)


class SinglePluginView(OrganizationView):
    katalogus_client: KATalogusClientV1
    plugin: KATalogusBoefje | KATalogusNormalizer

    def setup(self, request, *args, plugin_id: str, **kwargs):
        """
        Prepare organization info and KAT-alogus API client.
        """
        super().setup(request, *args, plugin_id=plugin_id, **kwargs)
        self.katalogus_client = get_katalogus(self.organization.code)

        try:
            self.plugin = self.katalogus_client.get_plugin(plugin_id)
            self.plugin_schema = self.katalogus_client.get_plugin_schema(plugin_id)
        except HTTPError as exc:
            if isinstance(exc, HTTPStatusError) and exc.response.status_code == HTTP_404_NOT_FOUND:
                raise Http404(f"Plugin {plugin_id} not found.")
            messages.add_message(
                self.request,
                messages.ERROR,
                _("Getting information for plugin {} failed. Please check the KATalogus logs.").format(plugin_id),
            )
            raise

    def dispatch(self, request, *args, **kwargs):
        if not self.plugin:
            return redirect(reverse("katalogus", kwargs={"organization_code": self.organization.code}))

        return super().dispatch(request, *args, **kwargs)

    def is_required_field(self, field: str) -> bool:
        """Check whether this field should be required, defaults to False."""
        return bool(self.plugin_schema and field in self.plugin_schema.get("required", []))

    def is_secret_field(self, field: str) -> bool:
        """Check whether this field should be secret, defaults to False."""
        return bool(self.plugin_schema and field in self.plugin_schema.get("secret", []))


class NormalizerMixin(OctopoesView):
    """
    When a user wants to run a normalizer on a given set of raw data,
    this mixin provides the method to construct the normalizer task for that data and run it.
    """

    def run_normalizer(self, normalizer: KATalogusNormalizer, raw_data: RawData) -> None:
        normalizer_task = NormalizerTask(normalizer=Normalizer(id=normalizer.id, version=None), raw_data=raw_data)

        task = PrioritizedItem(priority=1, data=normalizer_task)

        schedule_task(self.request, self.organization.code, task)


class BoefjeMixin(OctopoesView):
    """
    When a user wants to scan one or multiple OOI's,
    this mixin provides the methods to construct the boefjes for the OOI's and run them.
    """

    def run_boefje(self, katalogus_boefje: KATalogusBoefje, ooi: OOI | None) -> None:
        boefje_task = BoefjeTask(
            boefje=Boefje.model_validate(katalogus_boefje.model_dump()),
            input_ooi=ooi.reference if ooi else None,
            organization=self.organization.code,
        )

        task = PrioritizedItem(priority=1, data=boefje_task)
        schedule_task(self.request, self.organization.code, task)

    def run_boefje_for_oois(
        self,
        boefje: KATalogusBoefje,
        oois: list[OOI],
    ) -> None:
        if not oois and not boefje.consumes:
            self.run_boefje(boefje, None)

        for ooi in oois:
            if ooi.scan_profile and ooi.scan_profile.level < boefje.scan_level:
                self.can_raise_clearance_level(ooi, boefje.scan_level)
            self.run_boefje(boefje, ooi)
