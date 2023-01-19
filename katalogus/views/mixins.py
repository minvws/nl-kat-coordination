from logging import getLogger
from typing import List
from uuid import uuid4

from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from requests import HTTPError

from account.mixins import OrganizationView
from katalogus.client import get_katalogus
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

    def run_boefje(self, katalogus_boefje: Boefje, ooi: OOI) -> None:

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
            input_ooi=ooi.reference,
            organization=self.organization.code,
        )

        item = QueuePrioritizedItem(id=boefje_task.id, priority=1, data=boefje_task)
        logger.info("Item: %s", item.json())
        client.push_task(boefje_queue_name, item)

    def run_boefje_for_oois(
        self,
        boefje: Boefje,
        oois: List[OOI],
    ) -> None:

        for ooi in oois:
            if ooi.scan_profile.level < boefje.scan_level:
                try:
                    self.raise_clearance_level(ooi.reference, boefje.scan_level)
                except (IndemnificationNotPresentException, ClearanceLevelTooLowException):
                    continue
            self.run_boefje(boefje, ooi)

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
                _("Trying to run disabled boefje '{boefje_id}'.").format(boefje_id=boefje_id),
            )
            return

        ooi_ids = view_args.getlist("ooi")
        oois = [self.get_single_ooi(pk=ooi_id) for ooi_id in ooi_ids]

        try:
            self.run_boefje_for_oois(boefje, oois)
        except HTTPError:
            return

        success_message = _(
            "Your scan is running successfully in the background. \n "
            "Results will be added to the object list when they are in. "
            "It may take some time, a refresh of the page may be needed to show the results."
        )
        messages.add_message(self.request, messages.SUCCESS, success_message)
        return
