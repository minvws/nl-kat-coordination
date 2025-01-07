from django.urls import path

from . import views

# Crisis room overview urls
urlpatterns = [path("", views.CrisisRoom.as_view(), name="crisis_room")]
