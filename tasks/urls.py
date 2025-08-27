from django.urls import path

from tasks.views import TaskDetailView, TaskListView, ScheduleListView, ScheduleDetailView

urlpatterns = [
    path("new-tasks", TaskListView.as_view(), name="new_task_list"),
    path("new-tasks/<slug:pk>/", TaskDetailView.as_view(), name="task_detail"),
    path("schedule/", ScheduleListView.as_view(), name="schedule_list"),
    path("schedule/<slug:pk>/", ScheduleDetailView.as_view(), name="schedule_detail"),
]
