from django.urls import path

from tasks.views import TaskDetailView, TaskListView

urlpatterns = [
    path("", TaskListView.as_view(), name="task_list"),
    path("<slug:pk>/", TaskDetailView.as_view(), name="task_detail"),
]
