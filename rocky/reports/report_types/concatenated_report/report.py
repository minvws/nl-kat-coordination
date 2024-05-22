from django.utils.translation import gettext_lazy as _

from reports.report_types.definitions import Report


class ConcatenatedReport(Report):
    id = "concatinated-report"
    name = _("Concatenated Report")
