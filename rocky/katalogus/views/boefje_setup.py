import uuid
from datetime import datetime

from account.mixins import OrganizationPermissionRequiredMixin, OrganizationView
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.edit import FormView
from tools.forms.boefje import BoefjeAddForm

from katalogus.client import Boefje, get_katalogus
from octopoes.models.types import type_by_name


class BoefjeSetupView(OrganizationPermissionRequiredMixin, OrganizationView, FormView):
    """View where the user can create a new boefje"""

    template_name = "boefje_setup.html"
    form_class = BoefjeAddForm
    permission_required = "tools.can_set_katalogus_settings"

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

    def form_valid(self, form):
        """If the form is valid, redirect to the supplied URL."""
        form_data = form.cleaned_data
        input_object = {type_by_name(form_data["consumes"])}
        arguments = form_data["oci_arguments"].split()
        produces = form_data["produces"].replace(",", "").split()
        boefje_id = str(uuid.uuid4())

        boefje = Boefje(
            id=boefje_id,
            name=form_data["name"] or None,
            created=str(datetime.now()),
            description=form_data["description"] or None,
            enabled=False,
            type="boefje",
            scan_level=form_data["scan_level"],
            consumes=input_object,
            produces=produces,
            schema=form_data["schema"],
            oci_image=form_data["oci_image"] or None,
            oci_arguments=arguments,
        )

        get_katalogus(self.organization.code).create_plugin(boefje)

        return redirect(
            reverse("boefje_detail", kwargs={"organization_code": self.organization.code, "plugin_id": boefje_id})
        )
