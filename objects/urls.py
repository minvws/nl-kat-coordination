from django.urls import path

from objects.views import ObjectListView

urlpatterns = [
    path("objects/", ObjectListView.as_view(), name="object_list"),
    path("objects/<slug:organizatin_code>", ObjectListView.as_view(), name="object_list"),
]
