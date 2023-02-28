from django.views.generic import TemplateView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from fmea.views.view_helpers import FMEABreadcrumbsMixin


@class_view_decorator(otp_required)
class FMEAIndexView(FMEABreadcrumbsMixin, TemplateView):
    """
    The introduction page or main navigation for FMEA.
    """

    template_name = "fmea/fmea_index.html"
