import uuid
from urllib.parse import urlencode

from account.mixins import OrganizationPermissionRequiredMixin, OrganizationView
from django.urls import reverse
from django.views.generic.edit import FormView
from tools.forms.boefje import BoefjeAddForm

from katalogus.client import get_katalogus


class BoefjeSetupView(OrganizationPermissionRequiredMixin, OrganizationView, FormView):
    """Setup view for creating new Boefjes and variants"""

    template_name = "boefje_setup.html"
    permission_required = "tools.can_add_boefje"

    def get_form(self):
        return BoefjeAddForm(get_katalogus(self.organization.code), self.plugin_id, **self.get_form_kwargs())


class AddBoefjeView(BoefjeSetupView):
    """View where the user can create a new Boefje"""

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        self.plugin_id = str(uuid.uuid4())
        self.return_to_plugin_id = self.plugin_id

    def get_success_url(self) -> str:
        query_params = urlencode({"new_variant": True})
        return (
            reverse(
                "boefje_detail",
                kwargs={"organization_code": self.organization.code, "plugin_id": self.return_to_plugin_id},
            )
            + "?"
            + query_params
        )

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

    def get_initial(self):
        initial = super().get_initial()

        consumes = []

        for input_object in self.plugin.consumes:
            consumes.append(input_object.__name__)

        initial["oci_image"] = self.plugin.oci_image
        initial["oci_arguments"] = " ".join(self.plugin.oci_arguments)
        initial["schema"] = self.plugin.schema
        initial["consumes"] = consumes
        initial["produces"] = ", ".join(self.plugin.produces)
        initial["scan_level"] = self.plugin.scan_level

        return initial

    def get_success_url(self) -> str:
        if self.kwargs.get("plugin_id"):
            return reverse(
                "boefje_variant_setup",
                kwargs={"organization_code": self.organization.code, "plugin_id": self.plugin_id},
            )
        else:
            return reverse("boefje_setup", kwargs={"organization_code": self.organization.code})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["boefje_variant"] = True
        context["return_to_plugin_id"] = self.return_to_plugin_id

        context["breadcrumbs"] = [
            {"url": reverse("katalogus", kwargs={"organization_code": self.organization.code}), "text": "KAT-alogus"},
            {
                "url": reverse(
                    "boefje_detail",
                    kwargs={"organization_code": self.organization.code, "plugin_id": self.return_to_plugin_id},
                ),
                "text": "Boefje detail page",
            },
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

    def get_initial(self):
        initial = super().get_initial()

        consumes = []

        for input_object in self.plugin.consumes:
            consumes.append(input_object.__name__)

        initial["name"] = self.plugin.name
        initial["description"] = self.plugin.description
        initial["oci_image"] = self.plugin.oci_image
        initial["oci_arguments"] = " ".join(self.plugin.oci_arguments)
        initial["schema"] = self.plugin.schema
        initial["consumes"] = consumes
        initial["produces"] = ", ".join(self.plugin.produces)
        initial["scan_level"] = self.plugin.scan_level

        return initial

    def get_success_url(self) -> str:
        return reverse(
            "boefje_detail", kwargs={"organization_code": self.organization.code, "plugin_id": self.plugin.id}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["edit_boefje_name"] = self.plugin.name
        context["return_to_plugin_id"] = self.plugin.id

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
                "text": self.plugin.name,
            },
            {
                "url": reverse(
                    "edit_boefje",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_id": self.plugin.id,
                    },
                ),
                "text": 'Edit "' + self.plugin.name + '"',
            },
        ]

        return context
