import uuid
from datetime import datetime
from urllib.parse import urlencode

from account.mixins import OrganizationPermissionRequiredMixin, OrganizationView
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.edit import FormView
from tools.forms.boefje import BoefjeAddForm

from katalogus.client import Boefje, get_katalogus
from octopoes.models.types import type_by_name


class BoefjeSetupView(OrganizationPermissionRequiredMixin, OrganizationView, FormView):
    """Setup view for creating new Boefjes and variants"""

    template_name = "boefje_setup.html"
    form_class = BoefjeAddForm
    permission_required = "tools.can_add_boefje"

    def form_valid(self, form):
        """If the form is valid, redirect to the supplied URL."""
        form_data = form.cleaned_data

        plugin = create_boefje_with_form_data(form_data, self.plugin_id, str(datetime.now()))

        get_katalogus(self.organization.code).create_plugin(plugin)
        query_params = urlencode({"new_variant": True})

        return redirect(
            reverse(
                "boefje_detail",
                kwargs={"organization_code": self.organization.code, "plugin_id": self.return_to_plugin_id},
            )
            + "?"
            + query_params
        )


class AddBoefjeView(BoefjeSetupView):
    """View where the user can create a new Boefje"""

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        self.plugin_id = str(uuid.uuid4())
        self.return_to_plugin_id = self.plugin_id

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

        self.plugin_id = str(uuid.uuid4())
        self.return_to_plugin_id = self.kwargs.get("plugin_id")
        katalogus = get_katalogus(self.organization.code)
        self.plugin = katalogus.get_plugin(self.return_to_plugin_id)
        consumes = []

        for input_object in list(self.plugin.consumes):
            consumes.append(input_object.__name__)

        self.initial = {
            "oci_image": self.plugin.oci_image,
            "oci_arguments": ", ".join(self.plugin.oci_arguments),
            "schema": self.plugin.schema,
            "consumes": consumes,
            "produces": ", ".join(self.plugin.produces),
            "scan_level": self.plugin.scan_level,
        }

    def get_form(self, form_class=None) -> BoefjeAddForm:
        if form_class is None:
            form_class = self.get_form_class()

        form = super().get_form(form_class)
        form.fields["oci_image"].disabled = True

        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["boefje_variant"] = True

        context["breadcrumbs"] = [
            {"url": reverse("katalogus", kwargs={"organization_code": self.organization.code}), "text": "KAT-alogus"},
            {
                "url": reverse(
                    "boefje_variant_setup",
                    kwargs={"organization_code": self.organization.code, "plugin_id": self.return_to_plugin_id},
                ),
                "text": "Boefje variant setup",
            },
        ]

        return context


class EditBoefjeView(BoefjeSetupView):
    """View where the user can update a Boefje."""

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        plugin_id = self.kwargs.get("plugin_id")
        katalogus = get_katalogus(self.organization.code)
        self.plugin = katalogus.get_plugin(plugin_id)
        consumes = []

        for input_object in list(self.plugin.consumes):
            consumes.append(input_object.__name__)

        self.initial = {
            "name": self.plugin.name,
            "description": self.plugin.description,
            "oci_image": self.plugin.oci_image,
            "oci_arguments": ", ".join(self.plugin.oci_arguments),
            "schema": self.plugin.schema,
            "consumes": consumes,
            "produces": ", ".join(self.plugin.produces),
            "scan_level": self.plugin.scan_level,
        }

    def form_valid(self, form):
        """If the form is valid, redirect to the supplied URL."""
        form_data = form.cleaned_data
        plugin = create_boefje_with_form_data(form_data, self.kwargs.get("plugin_id"), self.plugin.created)

        get_katalogus(self.organization.code).edit_plugin(plugin)

        return redirect(
            reverse("boefje_detail", kwargs={"organization_code": self.organization.code, "plugin_id": plugin.id})
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["edit_boefje"] = self.plugin.name

        context["breadcrumbs"] = [
            {
                "url": reverse("katalogus", kwargs={"organization_code": self.organization.code}),
                "text": "KAT-alogus",
            },
            {
                "url": reverse(
                    "boefje_detail",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_id": self.plugin.id,
                    },
                ),
                "text": 'Edit "' + self.plugin.name + '"',
            },
        ]

        return context


def create_boefje_with_form_data(form_data, plugin_id, created):
    arguments = [] if form_data["oci_arguments"] == "" else form_data["oci_arguments"].split()
    consumes = [] if form_data["consumes"] == "" else form_data["consumes"].strip("[]").replace("'", "").split(", ")
    produces = [] if form_data["produces"] == "" else form_data["produces"].split(",")
    produces = [p.strip() for p in produces]
    input_objects = []

    for input_object in consumes:
        input_objects.append(type_by_name(input_object))

    return Boefje(
        id=plugin_id,
        name=form_data.get("name"),
        created=created,
        description=form_data.get("description"),
        enabled=False,
        type="boefje",
        scan_level=form_data["scan_level"],
        consumes=input_objects,
        produces=produces,
        schema=form_data["schema"],
        oci_image=form_data.get("oci_image"),
        oci_arguments=arguments,
    )
