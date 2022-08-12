from django.urls.base import reverse
from django.views.generic.detail import DetailView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator


@class_view_decorator(otp_required)
class AccountView(DetailView):
    template_name = "account_detail.html"

    def get_object(self):
        if "pk" not in self.kwargs:
            return self.request.user
        return super().get_object()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": "", "text": "Account details"},
        ]

        return context
