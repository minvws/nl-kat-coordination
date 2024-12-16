from django.urls import path

from . import views

# Crisis room overview urls
urlpatterns = [
    path("", views.CrisisRoomAllOrganizations.as_view(), name="crisis_room"),
    path("dashboards", views.CrisisRoomDashboards.as_view(), name="crisis_room_dashboards"),
    path("findings", views.CrisisRoomFindings.as_view(), name="crisis_room_findings"),
    path("settings/findings", views.DasboardFindingsSettings.as_view(), name="crisis_room_findings_settings"),
]
