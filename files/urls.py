from django.urls import path

from files.views import FileListView

urlpatterns = [path("files/", FileListView.as_view(), name="file_list")]
