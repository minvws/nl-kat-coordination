from django.urls.base import reverse_lazy
from django.utils.translation import gettext_lazy as _
from octopoes.models.ooi.findings import Finding

from rocky.views.ooi_view import BaseOOIListView
from tools.view_helpers import BreadcrumbsMixin


class FindingListView(BreadcrumbsMixin, BaseOOIListView):
    breadcrumbs = [{"url": reverse_lazy("finding_list"), "text": _("Findings")}]
    template_name = "findings/finding_list.html"
    ooi_types = {Finding}
