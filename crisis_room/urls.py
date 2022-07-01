from django.urls import path
from . import views

urlpatterns = [
    path("crisis-room/", views.CrisisRoomView.as_view(), name="crisis_room"),
]
