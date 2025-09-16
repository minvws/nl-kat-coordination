from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import TemplateView
from django.views.i18n import JavaScriptCatalog
from rest_framework import routers
from two_factor.urls import urlpatterns as tf_urls

from files.viewsets import FileViewSet
from objects.viewsets import ObjectViewSet
from openkat.views.health import Health, HealthChecks
from openkat.views.indemnification_add import IndemnificationAddView
from openkat.views.landing_page import LandingPageView
from openkat.views.organization_add import OrganizationAddView
from openkat.views.organization_edit import OrganizationEditView
from openkat.views.organization_list import OrganizationListView
from openkat.views.organization_member_add import (
    DownloadMembersTemplateView,
    MembersUploadView,
    OrganizationMemberAddAccountTypeView,
    OrganizationMemberAddView,
)
from openkat.views.organization_member_edit import OrganizationMemberEditView
from openkat.views.organization_member_list import OrganizationMemberListView
from openkat.views.organization_settings import OrganizationSettingsView
from openkat.views.privacy_statement import PrivacyStatementView
from openkat.viewsets import OrganizationViewSet
from tasks.viewsets import TaskViewSet

handler404 = "openkat.views.handler404.handler404"
handler403 = "openkat.views.handler403.handler403"

router = routers.SimpleRouter()
router.register(r"organization", OrganizationViewSet)
router.register(r"task", TaskViewSet, basename="task")
router.register(r"file", FileViewSet, basename="file")
router.register(r"objects", ObjectViewSet, basename="objects")

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("api/v1/", include(router.urls)),
    path("<organization_code>/health/", Health.as_view(), name="health"),
    path("", include(tf_urls)),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
]
urlpatterns += i18n_patterns(
    path("", include("account.urls"), name="account"),
    path("admin/", admin.site.urls),
    path("", LandingPageView.as_view(), name="landing_page"),
    path("onboarding/", include("onboarding.urls"), name="onboarding"),
    # New view:
    path("", include("plugins.urls"), name="plugins"),
    path("", include("tasks.urls"), name="tasks"),
    path("", include("files.urls"), name="files"),
    path("", include("objects.urls"), name="objects"),
    path("", include("oois.urls"), name="oois"),
    path("privacy-statement/", PrivacyStatementView.as_view(), name="privacy_statement"),
    path("organizations/", OrganizationListView.as_view(), name="organization_list"),
    path("organizations/add/", OrganizationAddView.as_view(), name="organization_add"),
    path("<organization_code>/settings/edit/", OrganizationEditView.as_view(), name="organization_edit"),
    path(
        "<organization_code>/settings/indemnifications/", IndemnificationAddView.as_view(), name="indemnification_add"
    ),
    path(
        "<organization_code>/members/add/",
        OrganizationMemberAddAccountTypeView.as_view(),
        name="organization_member_add_account_type",
    ),
    path(
        "<organization_code>/members/add/<account_type>/",
        OrganizationMemberAddView.as_view(),
        name="organization_member_add",
    ),
    path(
        "<organization_code>/members/upload/member_template",
        DownloadMembersTemplateView.as_view(),
        name="download_organization_member_template",
    ),
    path("<organization_code>/members/upload/", MembersUploadView.as_view(), name="organization_member_upload"),
    path("<organization_code>/settings", OrganizationSettingsView.as_view(), name="organization_settings"),
    path("<organization_code>/members", OrganizationMemberListView.as_view(), name="organization_member_list"),
    path(
        "<organization_code>/members/edit/<int:pk>/",
        OrganizationMemberEditView.as_view(),
        name="organization_member_edit",
    ),
    path("<organization_code>/health/v1/", HealthChecks.as_view(), name="health_beautified"),
)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# used by recurrence
urlpatterns += [path("jsi18n.js", JavaScriptCatalog.as_view(packages=["recurrence"]), name="jsi18n")]
