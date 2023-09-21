from django.urls import path

from reports.views import ReportOOISelectionView, ReportTypeSelectionView, ReportView

urlpatterns = [
    path("select/oois/", ReportOOISelectionView.as_view(), name="report_oois_selection"),
    path("select/report-type/", ReportTypeSelectionView.as_view(), name="report_type_selection"),
    path("view/", ReportView.as_view(), name="report_view"),
]
