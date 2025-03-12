from django.urls import path

from . import views

# Crisis room overview urls
urlpatterns = [
    path("", views.CrisisRoomView.as_view(), name="crisis_room"),
    path("<organization_code>/", views.OrganizationsCrisisRoomView.as_view(), name="organization_crisis_room"),
]
