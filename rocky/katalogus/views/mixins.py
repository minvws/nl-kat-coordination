from logging import getLogger
from typing import List, Optional, Union
from uuid import uuid4

from account.mixins import OrganizationView
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from requests import HTTPError, RequestException
from rest_framework.status import HTTP_404_NOT_FOUND

from katalogus.client import (
    Boefje as KATalogusBoefje,
)
from katalogus.client import (
    KATalogusClientV1,
    get_katalogus,
)
from katalogus.client import (
    Normalizer as KATalogusNormalizer,
)
from octopoes.models import OOI
from rocky.exceptions import (
    AcknowledgedClearanceLevelTooLowException,
    IndemnificationNotPresentException,
    TrustedClearanceLevelTooLowException,
)
from rocky.scheduler import Boefje, BoefjeTask, Normalizer, NormalizerTask, QueuePrioritizedItem, RawData, client
from rocky.views.mixins import OctopoesView

logger = getLogger(__name__)


class SinglePluginView(OrganizationView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.katalogus_client: Optional[KATalogusClientV1] = None
        self.plugin_schema = None
        self.plugin: Union[KATalogusBoefje, KATalogusNormalizer] = None

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
                raise Http404(f"Plugin {plugin_id} not found.")

            raise
        except RequestException:
            messages.add_message(
                self.request,
                messages.ERROR,
                _("Getting information for plugin {} failed. Please check the KATalogus logs.").format(plugin_id),
            )

    def dispatch(self, request, *args, **kwargs):
        if not self.plugin:
            return redirect(reverse("katalogus", kwargs={"organization_code": self.organization.code}))

        return super().dispatch(request, *args, **kwargs)

    def is_required_field(self, field: str) -> bool:
        return self.plugin_schema and field in self.plugin_schema.get("required", [])


class NormalizerMixin:
    """
    When a user wants to run a normalizer on a given set of raw data,
    this mixin provides the method to construct the normalizer task for that data and run it.
    """

    def run_normalizer(self, normalizer: KATalogusNormalizer, raw_data: RawData) -> None:
        normalizer_task = NormalizerTask(
            id=uuid4(), normalizer=Normalizer(id=normalizer.id, version=None), raw_data=raw_data
        )

        item = QueuePrioritizedItem(id=normalizer_task.id, priority=1, data=normalizer_task)
        client.push_task(f"normalizer-{self.organization.code}", item)


class BoefjeMixin(OctopoesView):
    """
    When a user wants to scan one or multiple OOI's,
    this mixin provides the methods to construct the boefjes for the OOI's and run them.
    """

    def run_boefje(self, katalogus_boefje: KATalogusBoefje, ooi: Optional[OOI]) -> None:
        boefje_task = BoefjeTask(
            id=uuid4().hex,
            boefje=Boefje.parse_obj(katalogus_boefje.dict()),
            input_ooi=ooi.reference if ooi else None,
            organization=self.organization.code,
        )

        item = QueuePrioritizedItem(id=boefje_task.id, priority=1, data=boefje_task)
        client.push_task(f"boefje-{self.organization.code}", item)

    def run_boefje_for_oois(
        self,
        boefje: KATalogusBoefje,
        oois: List[OOI],
    ) -> None:
        if not oois and not boefje.consumes:
            self.run_boefje(boefje, None)

        for ooi in oois:
            if ooi.scan_profile.level < boefje.scan_level:
                try:
                    self.raise_clearance_level(ooi.reference, boefje.scan_level)
                except IndemnificationNotPresentException:
                    messages.add_message(
                        self.request,
                        messages.ERROR,
                        _(
                            "Could not raise clearance level of %s to L%s. \
                            Indemnification not present at organization %s."
                        )
                        % (
                            ooi.reference.human_readable,
                            boefje.scan_level,
                            self.organization.name,
                        ),
                    )
                except TrustedClearanceLevelTooLowException:
                    messages.add_message(
                        self.request,
                        messages.ERROR,
                        _(
                            "Could not raise clearance level of %s to L%s. "
                            "You were trusted a clearance level of L%s. "
                            "Contact your administrator to receive a higher clearance."
                        )
                        % (
                            ooi.reference.human_readable,
                            boefje.scan_level,
                            self.organization_member.trusted_clearance_level,
                        ),
                    )
                except AcknowledgedClearanceLevelTooLowException:
                    messages.add_message(
                        self.request,
                        messages.ERROR,
                        _(
                            "Could not raise clearance level of %s to L%s. "
                            "You acknowledged a clearance level of L%s. "
                            "Please accept the clearance level first on your profile page to proceed."
                        )
                        % (
                            ooi.reference.human_readable,
                            boefje.scan_level,
                            self.organization_member.acknowledged_clearance_level,
                        ),
                    )

            self.run_boefje(boefje, ooi)
