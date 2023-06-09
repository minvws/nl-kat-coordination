from django.views.generic import TemplateView

from fmea.views.view_helpers import FMEABreadcrumbsMixin


class FMEAIndexView(FMEABreadcrumbsMixin, TemplateView):
    """
    The introduction page or main navigation for FMEA.
    """

    template_name = "fmea/fmea_index.html"
