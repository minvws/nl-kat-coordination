from django.urls import path

from tasks.views import ScheduleDetailView, ScheduleListView, ScheduleUpdateView, TaskDetailView, TaskListView, \
    ScheduleDeleteView

urlpatterns = [
    path("new-tasks", TaskListView.as_view(), name="new_task_list"),
    path("new-tasks/<slug:pk>/", TaskDetailView.as_view(), name="task_detail"),
    path("schedule/", ScheduleListView.as_view(), name="schedule_list"),
    path("schedule/<slug:pk>/", ScheduleDetailView.as_view(), name="schedule_detail"),
    path("schedule/<slug:pk>/edit", ScheduleUpdateView.as_view(), name="edit_schedule"),
    path("schedule/<slug:pk>/delete", ScheduleDeleteView.as_view(), name="delete_schedule"),
]
