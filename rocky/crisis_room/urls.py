from django.urls import path

from . import views

urlpatterns = [path("", views.CrisisRoomAllOrganizations.as_view(), name="crisis_room")]
