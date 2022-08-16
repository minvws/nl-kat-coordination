from django.urls.base import reverse_lazy
from django.views.generic import FormView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator
from account.forms import IndemnificationAddForm
from tools.models import OrganizationMember, Indemnification


@class_view_decorator(otp_required)
class IndemnificationAddView(FormView):
    template_name = "indemnification_add.html"
    form_class = IndemnificationAddForm
    success_url = reverse_lazy("indemnification_add")

    def form_valid(self, form):
        user = self.request.user
        organizationmember = OrganizationMember.objects.get(user=user)

        Indemnification.objects.create(
            user=user,
            organization=organizationmember.organization,
        )

        return super().form_valid(form)

    def get_template_names(self):
        template_name = "indemnification_add.html"

        if Indemnification.objects.filter(user=self.request.user):
            template_name = "indemnification_present.html"

        return [template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["breadcrumbs"] = [
            {"url": "", "text": "Indemnifications"},
        ]

        return context
