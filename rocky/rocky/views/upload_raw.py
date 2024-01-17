from urllib.parse import unquote

from account.mixins import OrganizationPermissionRequiredMixin, OrganizationView
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic.edit import FormView
from requests import HTTPError
from tools.forms.upload_raw import RAW_ERRORS, UploadRawForm

from rocky.bytes_client import get_bytes_client


class UploadRaw(OrganizationPermissionRequiredMixin, OrganizationView, FormView):
    template_name = "upload_raw.html"
    form_class = UploadRawForm
    permission_required = "tools.can_scan_organization"
    mime_types = False

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        initial = super().get_initial()
        if "mime_type" in self.kwargs:
            initial["mime_types"] = unquote(self.kwargs["mime_type"])
        elif "mime_types" in self.kwargs:
            initial["mime_types"] = unquote(self.kwargs["mime_type"])
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
        mime_types = form.cleaned_data["mime_types"]

        try:
            get_bytes_client(self.organization.code).upload_raw(raw_file.read(), mime_types)
        except HTTPError as e:
            message = _("Raw file could not be uploaded to Bytes: status code %s") % e.response.status_code

            return self.add_error_notification(message)

        self.add_success_notification(_("Raw file successfully added."))
