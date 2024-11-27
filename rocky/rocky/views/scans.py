from account.mixins import OrganizationView
from django.views.generic import TemplateView
from tools.view_helpers import Breadcrumb, ObjectsBreadcrumbsMixin


class ScanListView(ObjectsBreadcrumbsMixin, OrganizationView, TemplateView):
    template_name = "scan.html"

    def build_breadcrumbs(self) -> list[Breadcrumb]:
        breadcrumbs = super().build_breadcrumbs()

        breadcrumbs.append({"url": "", "text": "Scans"})

        return breadcrumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["boefjes"] = self.get_katalogus().get_enabled_boefjes()

        return context
