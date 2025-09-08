from django.urls import path

from objects.views import ObjectListView, ObjectSetCreateView, ObjectSetDetailView, ObjectSetListView

urlpatterns = [
    path("objects/", ObjectListView.as_view(), name="object_list"),
    path("objects/<slug:organizatin_code>/", ObjectListView.as_view(), name="object_list"),
    path("object-sets/", ObjectSetListView.as_view(), name="object_set_list"),
    path("object-sets/add/", ObjectSetCreateView.as_view(), name="add_object_set"),
    path("object-sets/<slug:pk>/", ObjectSetDetailView.as_view(), name="object_set_detail"),
]
