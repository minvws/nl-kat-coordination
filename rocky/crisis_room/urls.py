from django.urls import path

from . import views

# Crisis room overview urls
urlpatterns = [
    path("", views.CrisisRoomAllOrganizations.as_view(), name="crisis_room"),
    path("findings", views.CrisisRoomFindings.as_view(), name="crisis_room_findings"),
]
