from django.urls import path

from reports.views import ReportOOISelectionView, ReportSetupScanView, ReportTypeSelectionView, ReportView

urlpatterns = [
    path("select/oois/", ReportOOISelectionView.as_view(), name="report_oois_selection"),
    path("select/report-types/", ReportTypeSelectionView.as_view(), name="report_types_selection"),
    path("setup/scan/", ReportSetupScanView.as_view(), name="report_setup_scan"),
    path("view/", ReportView.as_view(), name="report_view"),
]
