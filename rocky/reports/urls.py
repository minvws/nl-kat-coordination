from django.urls import path

from reports.views import ReportOOISelectionView, ReportSelectionView, ReportTypeSelectionView

urlpatterns = [
    path("select/report-type/", ReportTypeSelectionView.as_view(), name="report_type_selection"),
    path("select/oois/", ReportOOISelectionView.as_view(), name="report_oois_selection"),
    path("view/", ReportSelectionView.as_view(), name="report_selection"),
]
