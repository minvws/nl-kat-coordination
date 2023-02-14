from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator
from django.urls import reverse_lazy
from account.forms import IndemnificationAddForm
from account.mixins import OrganizationView
from tools.models import Indemnification


@class_view_decorator(otp_required)
class IndemnificationAddView(OrganizationView, FormView):
    template_name = "indemnification_add.html"
    form_class = IndemnificationAddForm

    def post(self, request, *args, **kwargs):
        Indemnification.objects.get_or_create(
            user=self.request.user,
            organization=self.organization,
        )
        self.add_success_notification()
        return super().post(request, *args, **kwargs)

    def get_success_url(self) -> str:
        return reverse_lazy("organization_detail", kwargs={"organization_code": self.organization.code})

    def add_success_notification(self):
        success_message = _("Indemnification successfully set.")
        messages.add_message(self.request, messages.SUCCESS, success_message)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["indemnification_present"] = Indemnification.objects.filter(
            user=self.request.user, organization=self.organization
        )
        return context
