from logging import getLogger
from typing import List, Optional
from uuid import uuid4

from django.urls import reverse

from account.mixins import OrganizationView
from katalogus.client import get_katalogus, Plugin
from octopoes.models import OOI
from rocky.exceptions import IndemnificationNotPresentException, ClearanceLevelTooLowException
from rocky.scheduler import Boefje, BoefjeTask, QueuePrioritizedItem, client
from rocky.views.mixins import OctopoesView

logger = getLogger(__name__)


class KATalogusMixin(OrganizationView):
    def setup(self, request, *args, **kwargs):
        """
        Prepare organization info and KAT-alogus API client.
        """
        super().setup(request, *args, **kwargs)
        if request.user.is_anonymous:
            return reverse("login")
        else:
            self.katalogus_client = get_katalogus(self.organization.code)
            if "plugin_id" in kwargs:
                self.plugin_id = kwargs["plugin_id"]
                self.plugin = self.katalogus_client.get_plugin_details(self.plugin_id)
                self.plugin_schema = self.katalogus_client.get_plugin_schema(self.plugin_id)


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
