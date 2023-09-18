from django.urls import path

from reports.views import GenerateReportView, OOIReportView, ReportView

urlpatterns = [
    path("", ReportView.as_view(), name="reports"),
    path("ooi-report/", OOIReportView.as_view(), name="ooi_report"),
    path("<report_type>/generate/", GenerateReportView.as_view(), name="generate_report"),
]
