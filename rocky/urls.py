from django.urls import path, include
from django.contrib import admin
from two_factor.urls import urlpatterns as tf_urls
from django.views.generic.base import TemplateView
from rest_framework import routers
from rocky import views
from tools.viewsets import OrganizationViewSet

handler404 = "rocky.views.handler404"

router = routers.SimpleRouter()
router.register(r"organization", OrganizationViewSet)

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("", views.LandingPageView.as_view(), name="landing_page"),
    path("account/", include("account.urls"), name="account"),
    path("", include(tf_urls)),
    path(
        "indemnifications/",
        views.IndemnificationAddView.as_view(),
        name="indemnification_add",
    ),
    path("switch_client/", views.switch_client, name="switch_client"),
    path("findings/", views.FindingListView.as_view(), name="finding_list"),
    path("findings/add/", views.FindingAddView.as_view(), name="finding_add"),
    path("finding_type/add/", views.FindingTypeAddView.as_view(), name="finding_type_add"),
    path("objects/graph/", views.OOIGraphView.as_view(), name="ooi_graph"),
    path("objects/report/", views.OOIReportView.as_view(), name="ooi_report"),
    path("objects/report/pdf/", views.OOIReportPDFView.as_view(), name="ooi_pdf_report"),
    path("objects/summary/", views.OOISummaryView.as_view(), name="ooi_summary"),
    path("objects/tree/", views.OOITreeView.as_view(), name="ooi_tree"),
    path("objects/findings/", views.OOIFindingListView.as_view(), name="ooi_findings"),
    path("organizations/", views.OrganizationListView.as_view(), name="organization_list"),
    path(
        "organizations/add/",
        views.OrganizationAddView.as_view(),
        name="organization_add",
    ),
    path(
        "organizations/<path:pk>/edit/",
        views.OrganizationEditView.as_view(),
        name="organization_edit",
    ),
    path(
        "organizations/<path:pk>/members/add/",
        views.OrganizationMemberAddView.as_view(),
        name="organization_member_add",
    ),
    path(
        "organizations/<path:pk>/members/",
        views.OrganizationMemberListView.as_view(),
        name="organization_member_list",
    ),
    path(
        "organizations/<path:pk>/",
        views.OrganizationDetailView.as_view(),
        name="organization_detail",
    ),
    path(
        "organization_members/<path:pk>/edit/",
        views.OrganizationMemberEditView.as_view(),
        name="organization_member_edit",
    ),
    path("health/", views.health, name="health"),
    path(
        "health/v1/",
        views.HealthChecks.as_view(),
        name="health_beautified",
    ),
    path("objects/", views.OOIListView.as_view(), name="ooi_list"),
    path("objects/add/", views.OOIAddTypeSelectView.as_view(), name="ooi_add_type_select"),
    path(
        "objects/add-related/",
        views.OOIRelatedObjectAddView.as_view(),
        name="ooi_add_related",
    ),
    path("objects/add/<ooi_type>/", views.OOIAddView.as_view(), name="ooi_add"),
    path("objects/edit/", views.OOIEditView.as_view(), name="ooi_edit"),
    path("objects/delete/", views.OOIDeleteView.as_view(), name="ooi_delete"),
    path("objects/detail/", views.OOIDetailView.as_view(), name="ooi_detail"),
    path("objects/export", views.OOIListExportView.as_view(), name="ooi_list_export"),
    path(
        "objects/indemnification/reset/",
        views.ScanProfileResetView.as_view(),
        name="scan_profile_reset",
    ),
    path(
        "objects/scan-profile/",
        views.ScanProfileDetailView.as_view(),
        name="scan_profile_detail",
    ),
    path("scans/", views.ScanListView.as_view(), name="scan_list"),
    path("admin/", admin.site.urls),
    path(
        "upload/csv/",
        views.UploadCSV.as_view(),
        name="upload_csv",
    ),
    path("signal_qr/", views.SignalQRView.as_view(), name="signal_qr"),
    path(
        "privacy-statement/",
        views.PrivacyStatementView.as_view(),
        name="privacy_statement",
    ),
    path("onboarding/", include("onboarding.urls"), name="onboarding"),
    path("crisis-room/", include("crisis_room.urls"), name="crisis_room"),
    path("tasks/", views.BoefjesTaskListView.as_view(), name="task_list"),
    path("tasks/boefjes", views.BoefjesTaskListView.as_view(), name="boefjes_task_list"),
    path(
        "tasks/normalizers",
        views.NormalizersTaskListView.as_view(),
        name="normalizers_task_list",
    ),
    path(
        "tasks/<task_id>/download/",
        views.DownloadTaskDetail.as_view(),
        name="download_task_meta",
    ),
    path("bytes/<boefje_meta_id>/raw", views.BytesRawView.as_view(), name="bytes_raw"),
    path("onboarding/", include("onboarding.urls"), name="onboarding"),
    path("kat-alogus/", include("katalogus.urls"), name="katalogus"),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    path("api/v1/", include(router.urls)),
]
