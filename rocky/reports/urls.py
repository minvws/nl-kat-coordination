from django.urls import path

from reports.views.aggregate_report import (
    LandingAggregateReportView,
    OOISelectionAggregateReportView,
    ReportTypesSelectionAggregateReportView,
    SaveAggregateReportView,
    SetupScanAggregateReportView,
)
from reports.views.base import ReportsLandingView, ViewReportPDFView, ViewReportView
from reports.views.generate_report import (
    LandingGenerateReportView,
    OOISelectionGenerateReportView,
    ReportTypesSelectionGenerateReportView,
    SaveGenerateReportView,
    SetupScanGenerateReportView,
)
from reports.views.multi_report import (
    LandingMultiReportView,
    MultiReportPDFView,
    MultiReportView,
    OOISelectionMultiReportView,
    ReportTypesSelectionMultiReportView,
    SetupScanMultiReportView,
)
from reports.views.report_overview import ReportHistoryView, SubreportView

# Report overview urls
urlpatterns = [
    path("", ReportsLandingView.as_view(), name="reports"),
    path("report-history/", ReportHistoryView.as_view(), name="report_history"),
    path("report-history/subreports", SubreportView.as_view(), name="subreports"),
]

# View report urls
urlpatterns += [
    path("view", ViewReportView.as_view(), name="view_report"),
    path("view/pdf/", ViewReportPDFView.as_view(), name="view_report_pdf"),
]

# Generate report urls
urlpatterns += [
    path("generate-report/", LandingGenerateReportView.as_view(), name="generate_report_landing"),
    path("generate-report/select/oois/", OOISelectionGenerateReportView.as_view(), name="generate_report_select_oois"),
    path(
        "generate-report/select/report-types/",
        ReportTypesSelectionGenerateReportView.as_view(),
        name="generate_report_select_report_types",
    ),
    path("generate-report/setup-scan/", SetupScanGenerateReportView.as_view(), name="generate_report_setup_scan"),
    path("generate-report/view/", SaveGenerateReportView.as_view(), name="generate_report_view"),
]

# Aggregate report urls
urlpatterns += [
    path("aggregate-report/", LandingAggregateReportView.as_view(), name="aggregate_report_landing"),
    path(
        "aggregate-report/select/oois/", OOISelectionAggregateReportView.as_view(), name="aggregate_report_select_oois"
    ),
    path(
        "aggregate-report/select/report-types/",
        ReportTypesSelectionAggregateReportView.as_view(),
        name="aggregate_report_select_report_types",
    ),
    path("aggregate-report/setup-scan/", SetupScanAggregateReportView.as_view(), name="aggregate_report_setup_scan"),
    path("aggregate-report/view/", SaveAggregateReportView.as_view(), name="aggregate_report_save"),
]

# Multi report urls
urlpatterns += [
    path("multi-report/", LandingMultiReportView.as_view(), name="multi_report_landing"),
    path("multi-report/select/oois/", OOISelectionMultiReportView.as_view(), name="multi_report_select_oois"),
    path(
        "multi-report/select/report-types/",
        ReportTypesSelectionMultiReportView.as_view(),
        name="multi_report_select_report_types",
    ),
    path("multi-report/setup-scan/", SetupScanMultiReportView.as_view(), name="multi_report_setup_scan"),
    path("multi-report/view/", MultiReportView.as_view(), name="multi_report_view"),
    path("multi-report/view/pdf/", MultiReportPDFView.as_view(), name="multi_report_pdf"),
]
