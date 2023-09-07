from django.urls import path

from reports.views import GenerateReportView, ReportsView

urlpatterns = [
    path("", ReportsView.as_view(), name="reports"),
    path("/generate/", GenerateReportView.as_view(), name="generate_report"),
]
