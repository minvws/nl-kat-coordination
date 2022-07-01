from typing import List, Dict

from rocky.views.boefje import BoefjeMixin
from rocky.views.ooi_view import BaseOOIDetailView, OOIBreadcrumbsMixin
from tools.forms import ObservedAtForm
from tools.ooi_helpers import (
    get_finding_type_from_finding,
    get_knowledge_base_data_for_ooi,
)
from rocky.views.ooi_detail_related_object import OOIFindingManager
from tools.view_helpers import Breadcrumb, get_ooi_url
from django.utils.translation import gettext_lazy as _


class OOIFindingListView(
    OOIFindingManager, BoefjeMixin, BaseOOIDetailView, OOIBreadcrumbsMixin
):
    template_name = "oois/ooi_findings.html"
    connector_form_class = ObservedAtForm

    def build_breadcrumbs(self) -> List[Breadcrumb]:
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append(self.get_last_breadcrumb())
        return breadcrumbs

    def get_last_breadcrumb(self):
        return {
            "url": get_ooi_url("ooi_findings", self.ooi.primary_key),
            "text": _("Object findings"),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["findings"] = self.get_finding_details_sorted_by_score_desc()
        context["breadcrumbs"] = self.build_breadcrumbs()
        return context
