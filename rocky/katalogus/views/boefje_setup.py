import uuid
from datetime import datetime
from urllib.parse import urlencode

import structlog
from account.mixins import OrganizationPermissionRequiredMixin, OrganizationView
from django.urls import reverse
from django.views.generic.edit import FormView
from tools.forms.boefje import BoefjeSetupForm

from katalogus.client import Boefje, DuplicatePluginError, KATalogusNotAllowedError, get_katalogus
from octopoes.models.types import type_by_name

logger = structlog.get_logger(__name__)


class BoefjeSetupView(OrganizationPermissionRequiredMixin, OrganizationView, FormView):
    """Setup view for creating new Boefjes and variants"""

    template_name = "boefje_setup.html"
    form_class = BoefjeSetupForm
    permission_required = "tools.can_add_boefje"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.katalogus = get_katalogus(self.organization.code)
        self.plugin_id = uuid.uuid4()
        self.created = str(datetime.now())
        self.query_params = urlencode({"new_variant": True})

    def get_success_url(self) -> str:
        return (
            reverse("boefje_detail", kwargs={"organization_code": self.organization.code, "plugin_id": self.plugin_id})
            + "?"
            + self.query_params
        )


class AddBoefjeView(BoefjeSetupView):
    """View where the user can create a new Boefje"""

    def form_valid(self, form):
        form_data = form.cleaned_data
        plugin = create_boefje_with_form_data(form_data, self.plugin_id, self.created)

        try:
            logger.info("Creating boefje", event_code=800025, boefje=plugin)
            self.katalogus.create_plugin(plugin)
            return super().form_valid(form)
        except DuplicatePluginError as error:
            if "name" in error.message:
                form.add_error("name", ("Boefje with this name does already exist. Please choose another name."))
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["breadcrumbs"] = [
            {"url": reverse("katalogus", kwargs={"organization_code": self.organization.code}), "text": "KAT-alogus"},
            {
                "url": reverse("boefje_setup", kwargs={"organization_code": self.organization.code}),
                "text": "Boefje setup",
            },
        ]

        return context


class AddBoefjeVariantView(BoefjeSetupView):
    """View where the user can create a Boefje variant, based on another Boefje."""

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        self.based_on_plugin_id = self.kwargs.get("plugin_id")

        self.plugin = self.katalogus.get_plugin(self.based_on_plugin_id)

    def get_initial(self):
        initial = super().get_initial()

        consumes = []

        for input_object in self.plugin.consumes:
            consumes.append(input_object.__name__)

        initial["oci_image"] = self.plugin.oci_image
        initial["oci_arguments"] = " ".join(self.plugin.oci_arguments)
        initial["boefje_schema"] = self.plugin.boefje_schema
        initial["consumes"] = consumes
        initial["produces"] = ", ".join(self.plugin.produces)
        initial["scan_level"] = self.plugin.scan_level
        initial["interval"] = self.plugin.interval

        return initial

    def form_valid(self, form):
        form_data = form.cleaned_data
        plugin = create_boefje_with_form_data(form_data, self.plugin_id, self.created)

        try:
            logger.info("Creating boefje", event_code=800025, boefje=plugin)
            self.katalogus.create_plugin(plugin)
            return super().form_valid(form)
        except DuplicatePluginError as error:
            if "name" in error.message:
                form.add_error("name", ("Boefje with this name does already exist. Please choose another name."))
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["boefje_variant"] = True
        context["return_to_plugin_id"] = self.based_on_plugin_id

        context["breadcrumbs"] = [
            {"url": reverse("katalogus", kwargs={"organization_code": self.organization.code}), "text": "KAT-alogus"},
            {
                "url": reverse(
                    "boefje_detail",
                    kwargs={"organization_code": self.organization.code, "plugin_id": self.based_on_plugin_id},
                ),
                "text": "Boefje detail page",
            },
            {
                "url": reverse(
                    "boefje_variant_setup",
                    kwargs={"organization_code": self.organization.code, "plugin_id": self.based_on_plugin_id},
                ),
                "text": "Boefje variant setup",
            },
        ]

        return context


class EditBoefjeView(BoefjeSetupView):
    """View where the user can update a Boefje."""

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        self.plugin_id = self.kwargs.get("plugin_id")
        self.query_params = urlencode({"new_variant": False})
        self.plugin = self.katalogus.get_plugin(self.plugin_id)
        self.created = self.plugin.created

    def get_initial(self):
        initial = super().get_initial()

        consumes = []

        for input_object in self.plugin.consumes:
            consumes.append(input_object.__name__)

        initial["name"] = self.plugin.name
        initial["description"] = self.plugin.description
        initial["oci_image"] = self.plugin.oci_image
        initial["oci_arguments"] = " ".join(self.plugin.oci_arguments)
        initial["boefje_schema"] = self.plugin.boefje_schema
        initial["consumes"] = consumes
        initial["produces"] = ", ".join(self.plugin.produces)
        initial["scan_level"] = self.plugin.scan_level
        initial["interval"] = self.plugin.interval

        return initial

    def form_valid(self, form):
        form_data = form.cleaned_data
        plugin = create_boefje_with_form_data(form_data, self.plugin_id, self.created)

        try:
            logger.info("Editing boefje", event_code=800026, boefje=plugin)
            self.katalogus.edit_plugin(plugin)
            return super().form_valid(form)
        except DuplicatePluginError as error:
            if "name" in error.message:
                form.add_error("name", ("Boefje with this name does already exist. Please choose another name."))
            return self.form_invalid(form)
        except KATalogusNotAllowedError:
            form.add_error(
                "name",
                (
                    "Editing this Boefje is not allowed because it is static. "
                    "Please create a new variant of this static Boefje."
                ),
            )
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["edit_boefje_name"] = self.plugin.name
        context["return_to_plugin_id"] = self.plugin.id

        context["breadcrumbs"] = [
            {"url": reverse("katalogus", kwargs={"organization_code": self.organization.code}), "text": "KAT-alogus"},
            {
                "url": reverse(
                    "boefje_detail", kwargs={"organization_code": self.organization.code, "plugin_id": self.plugin.id}
                ),
                "text": self.plugin.name,
            },
            {
                "url": reverse(
                    "edit_boefje", kwargs={"organization_code": self.organization.code, "plugin_id": self.plugin.id}
                ),
                "text": 'Edit "' + self.plugin.name + '"',
            },
        ]

        return context


def create_boefje_with_form_data(form_data, plugin_id: str, created: str):
    arguments = [] if not form_data["oci_arguments"] else form_data["oci_arguments"].split()
    consumes = [] if not form_data["consumes"] else form_data["consumes"].strip("[]").replace("'", "").split(", ")
    produces = [] if not form_data["produces"] else form_data["produces"].split(",")
    produces = {p.strip() for p in produces}
    interval = int(form_data.get("interval") or 0) or None
    input_objects = set()

    for input_object in consumes:
        input_objects.add(type_by_name(input_object))

    return Boefje(
        id=str(plugin_id),
        name=form_data["name"],
        created=created,
        description=form_data["description"],
        interval=interval,
        enabled=False,
        type="boefje",
        scan_level=form_data["scan_level"],
        consumes=input_objects,
        produces=produces,
        boefje_schema=form_data["boefje_schema"],
        oci_image=form_data["oci_image"],
        oci_arguments=arguments,
    )
