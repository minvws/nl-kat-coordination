from django.urls import path

from reports.views import (
    ReportCreateView,
    ReportDataDownloadView,
    ReportDetailView,
    ReportDownloadView,
    ReportHTMLView,
    ReportListView,
)

urlpatterns = [
    path("", ReportListView.as_view(), name="report_list"),
    path("add/", ReportCreateView.as_view(), name="add_report"),
    path("<slug:pk>/", ReportDetailView.as_view(), name="report_detail"),
    path("<slug:pk>/download/", ReportDownloadView.as_view(), name="download_report"),
    path("<slug:pk>/html/", ReportHTMLView.as_view(), name="report_html"),
    path("<slug:pk>/data/", ReportDataDownloadView.as_view(), name="report_data"),
]
