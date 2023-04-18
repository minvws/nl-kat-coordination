from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_otp.decorators import otp_required
from tools.view_helpers import get_ooi_url
from two_factor.views.utils import class_view_decorator

from rocky.views.mixins import SingleOOIMixin


@class_view_decorator(otp_required)
class OOIDeleteView(SingleOOIMixin, TemplateView):
    template_name = "oois/ooi_delete.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.ooi = self.get_ooi()

    def delete(self, request):
        self.octopoes_api_connector.delete(self.ooi.reference)
        return HttpResponseRedirect(self.get_success_url())

    # Add support for browsers which only accept GET and POST for now.
    def post(self, request, **kwargs):
        return self.delete(request)

    def get_success_url(self):
        return reverse_lazy("ooi_list", kwargs={"organization_code": self.organization.code})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Construct breadcrumbs
        breadcrumb_list = self.get_breadcrumb_list()
        breadcrumb_list.append(
            {
                "url": get_ooi_url("ooi_delete", self.ooi.primary_key, organization_code=self.organization.code),
                "text": _("Delete"),
            }
        )

        context["ooi"] = self.ooi
        context["props"] = self.ooi.dict()
        context["breadcrumbs"] = breadcrumb_list

        return context
