from logging import getLogger
from typing import List

from django.views.generic import TemplateView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from katalogus.client import get_katalogus
from tools.view_helpers import Breadcrumb, ObjectsBreadcrumbsMixin

logger = getLogger(__name__)


@class_view_decorator(otp_required)
class ScanListView(ObjectsBreadcrumbsMixin, TemplateView):
    template_name = "scan.html"

    def build_breadcrumbs(self) -> List[Breadcrumb]:
        breadcrumbs = super().build_breadcrumbs()

        breadcrumbs.append(
            {"url": "", "text": "Scans"},
        )

        return breadcrumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["boefjes"] = get_katalogus(
            self.request.active_organization.code
        ).get_enabled_boefjes()

        return context
