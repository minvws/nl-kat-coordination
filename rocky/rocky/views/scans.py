from logging import getLogger

from django.views.generic import TemplateView
from katalogus.client import get_katalogus
from tools.view_helpers import Breadcrumb, ObjectsBreadcrumbsMixin

logger = getLogger(__name__)


class ScanListView(ObjectsBreadcrumbsMixin, TemplateView):
    template_name = "scan.html"

    def build_breadcrumbs(self) -> list[Breadcrumb]:
        breadcrumbs = super().build_breadcrumbs()

        breadcrumbs.append(
            {"url": "", "text": "Scans"},
        )

        return breadcrumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["boefjes"] = get_katalogus(self.organization.code).get_enabled_boefjes()

        return context
