from django.urls import path

from reports.views import (
    AggregateReportTypeSelectionView,
    AggregateReportView,
    GenerateReportView,
    ReportOOISelectionView,
    ReportSetupScanView,
    ReportTypeSelectionView,
    ReportView,
)

urlpatterns = [
    path("", ReportView.as_view(), name="reports"),
    path("generate-report/", ReportView.as_view(), name="generate_report"),
    path("aggregate-report/", AggregateReportView.as_view(), name="aggregate_report"),
    path("aggregate-report/report-types/", AggregateReportTypeSelectionView.as_view(), name="aggregate_report_types"),
    path("select/oois/", ReportOOISelectionView.as_view(), name="report_oois_selection"),
    path("select/report-types/", ReportTypeSelectionView.as_view(), name="report_types_selection"),
    path("setup/scan/", ReportSetupScanView.as_view(), name="report_setup_scan"),
    path("view/", GenerateReportView.as_view(), name="generate_report_view"),
]
