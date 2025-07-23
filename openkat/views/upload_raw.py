from datetime import datetime, timezone
from urllib.parse import unquote

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic.edit import FormView

from account.mixins import OrganizationPermissionRequiredMixin, OrganizationView
from octopoes.models.types import OOI_TYPES
from openkat.forms.upload_raw import UploadRawForm
from tasks.models import NamedContent, RawFile


class UploadRaw(OrganizationPermissionRequiredMixin, OrganizationView, FormView):
    template_name = "upload_raw.html"
    form_class = UploadRawForm
    permission_required = "openkat.can_scan_organization"

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        initial = super().get_initial()
        if "mime_type" in self.kwargs:
            initial["mime_types"] = unquote(self.kwargs["mime_type"])
        elif "mime_types" in self.kwargs:
            initial["mime_types"] = unquote(self.kwargs["mime_types"])
        return initial

    def get_success_url(self):
        return reverse_lazy("ooi_list", kwargs={"organization_code": self.organization.code})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("ooi_list", kwargs={"organization_code": self.organization.code}), "text": _("Objects")},
            {
                "url": reverse("upload_raw", kwargs={"organization_code": self.organization.code}),
                "text": _("Upload raw"),
            },
        ]
        return context

    def form_valid(self, form):
        if not self.process_raw(form):
            return redirect("upload_raw", organization_code=self.organization.code)
        return super().form_valid(form)

    def add_error_notification(self, error_message):
        messages.add_message(self.request, messages.ERROR, error_message)
        return False

    def add_success_notification(self, success_message):
        messages.add_message(self.request, messages.SUCCESS, success_message)
        return True

    def process_raw(self, form):
        raw_file = form.cleaned_data["raw_file"]
        RawFile.objects.create(file=NamedContent(raw_file.file.read()))
        self.add_success_notification(_("Raw file successfully added."))

    def get_form_kwargs(self):
        kwargs = {"connector": self.octopoes_api_connector, "ooi_list": self.get_ooi_options()}
        kwargs.update(super().get_form_kwargs())

        if "ooi_class" in kwargs:
            del kwargs["ooi_class"]

        observed_at = self.request.GET.get("observed_at")
        if observed_at:
            kwargs["observed_at"] = observed_at

        return kwargs

    def get_ooi_options(self) -> list[tuple[str, str]]:
        objects = self.octopoes_api_connector.list_objects(
            set(OOI_TYPES.values()), valid_time=datetime.now(timezone.utc)
        ).items

        options = [(o.primary_key, o.get_ooi_type()) for o in objects]

        return options
