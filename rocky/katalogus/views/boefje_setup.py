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
        arguments = form_data["oci_arguments"].split(", ")
        input_objects = []
        consumes = form_data["consumes"].strip("[]'").split("', '")
        produces = form_data["produces"].split(", ")
        boefje_id = str(uuid.uuid4())

        for input_object in consumes:
            input_objects.append(type_by_name(input_object))

        if self.kwargs["plugin_id"]:
            original_boefje_id = self.kwargs["plugin_id"]
        else:
            original_boefje_id = boefje_id

        boefje = Boefje(
            id=boefje_id,
            name=form_data["name"] or None,
            created=str(datetime.now()),
            description=form_data["description"] or None,
            enabled=False,
            type="boefje",
            scan_level=form_data["scan_level"],
            consumes=input_objects,
            produces=produces,
            schema=form_data["schema"],
            oci_image=form_data["oci_image"] or None,
            oci_arguments=arguments,
        )

        get_katalogus(self.organization.code).create_plugin(boefje)
        query_params = urlencode({"new_variant": True})

        return redirect(
            reverse(
                "boefje_detail", kwargs={"organization_code": self.organization.code, "plugin_id": original_boefje_id}
            )
            + "?"
            + query_params
        )


class AddBoefjeView(BoefjeSetupView, OrganizationPermissionRequiredMixin, OrganizationView, FormView):
    """View where the user can create a new Boefje"""

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


class AddBoefjeVariantView(BoefjeSetupView, OrganizationPermissionRequiredMixin, OrganizationView, FormView):
    """View where the user can create a Boefje variant, based on another Boefje."""

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        plugin_id = self.kwargs["plugin_id"]
        katalogus = get_katalogus(self.organization.code)
        boefje = katalogus.get_plugin(plugin_id)
        consumes = []

        for input_object in list(boefje.consumes):
            consumes.append(input_object.__name__)

        self.initial = {
            "oci_image": boefje.oci_image,
            "oci_arguments": ", ".join(boefje.oci_arguments),
            "schema": boefje.schema,
            "consumes": consumes,
            "produces": ", ".join(boefje.produces),
            "scan_level": boefje.scan_level,
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
                    kwargs={"organization_code": self.organization.code, "plugin_id": self.kwargs["plugin_id"]},
                ),
                "text": "Boefje variant setup",
            },
        ]

        return context
