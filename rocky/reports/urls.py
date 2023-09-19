from django.urls import path

from reports.views import ReportOOISelectionView, ReportTypeSelectionView, ReportView

urlpatterns = [
    path("select/report-type/", ReportTypeSelectionView.as_view(), name="report_type_selection"),
    path("select/ooi/", ReportOOISelectionView.as_view(), name="report_ooi_selection"),
    path("view/", ReportView.as_view(), name="report_view"),
]
