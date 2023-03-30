from django.urls import path

from . import views

urlpatterns = [
    path("", views.CrisisRoomView.as_view(), name="crisis_room"),
]
