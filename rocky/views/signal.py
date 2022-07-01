from django.contrib import messages
from django.http import Http404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from rocky.settings import MIAUW_API_ENABLED
from tools.miauw_helpers import get_signal_linking_qr


@class_view_decorator(otp_required)
class SignalQRView(TemplateView):
    template_name = "signal_qr.html"

    def get(self, request, *args, **kwargs):
        if not MIAUW_API_ENABLED:
            raise Http404()

        return super().get(request, *args, **kwargs)

    def get_qr_code(self):
        try:
            return get_signal_linking_qr()
        except Exception as e:
            messages.add_message(self.request, messages.WARNING, str(e))
            return None

    def get_context_data(self, **kwargs):
        return {
            "breadcrumb_list": [
                {"url": reverse("signal_qr"), "text": _("Signal QR")},
            ],
            "signal_qr_base_64": self.get_qr_code(),
        }
