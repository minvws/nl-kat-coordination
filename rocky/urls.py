from django.urls import path, include
from django.contrib import admin
from two_factor.urls import urlpatterns as tf_urls
from django.views.generic.base import TemplateView
from crisis_room import views as crisis_room_views
from . import views

handler404 = "rocky.views.handler404"

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
    path(
        "finding_type/add/", views.FindingTypeAddView.as_view(), name="finding_type_add"
    ),
    path("objects/graph/", views.OOIGraphView.as_view(), name="ooi_graph"),
    path("objects/report/", views.OOIReportView.as_view(), name="ooi_report"),
    path("objects/summary/", views.OOISummaryView.as_view(), name="ooi_summary"),
    path("objects/tree/", views.OOITreeView.as_view(), name="ooi_tree"),
    path("objects/findings/", views.OOIFindingListView.as_view(), name="ooi_findings"),
    path(
        "organizations/", views.OrganizationListView.as_view(), name="organization_list"
    ),
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
    path("objects/", views.OOIListView.as_view(), name="ooi_list"),
    path(
        "objects/add/", views.OOIAddTypeSelectView.as_view(), name="ooi_add_type_select"
    ),
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
    path("upload/", views.upload, name="upload"),
    path("signal_qr/", views.SignalQRView.as_view(), name="signal_qr"),
    path("kat-alogus/", views.KATalogusListView.as_view(), name="katalogus"),
    path(
        "plugins/<boefje_id>/cover.png",
        views.BoefjeCoverView.as_view(),
        name="boefje_cover",
    ),
    path(
        "kat-alogus/<id>/",
        views.BoefjeDetailView.as_view(),
        name="katalogus_detail",
    ),
    path(
        "kat-alogus/<id>/add-consumable-object",
        views.BoefjeConsumableObjectType.as_view(),
        name="boefje_add_consumable_type",
    ),
    path(
        "kat-alogus/<id>/add-consumable-object/<add_ooi_type>",
        views.BoefjeConsumableObjectAddView.as_view(),
        name="boefje_add_consumable_object",
    ),
    path(
        "privacy-statement/",
        views.PrivacyStatementView.as_view(),
        name="privacy_statement",
    ),
    path(
        "crisis-room/",
        crisis_room_views.CrisisRoomView.as_view(),
        name="crisis_room",
    ),
    path("tasks/", views.TaskListView.as_view(), name="task_list"),
    path("bytes/<boefje_meta_id>/raw", views.BytesRawView.as_view(), name="bytes_raw"),
    path("onboarding/", include("onboarding.urls"), name="onboarding"),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
]
