from django.urls import path

from files.views import FileListView, FileCreateView

urlpatterns = [
    path("files/", FileListView.as_view(), name="file_list"),
    path("files/add/", FileCreateView.as_view(), name="add_file"),
]
