from django.urls import path

from tasks.views import (
    ScheduleCreateView,
    ScheduleDeleteView,
    ScheduleDetailView,
    ScheduleListView,
    ScheduleRunView,
    ScheduleUpdateView,
    TaskDetailView,
    TaskListView,
    TaskRescheduleView,
)

urlpatterns = [
    path("new-tasks/", TaskListView.as_view(), name="new_task_list"),
    path("new-tasks/<slug:pk>/", TaskDetailView.as_view(), name="task_detail"),
    path("new-tasks/<slug:task_id>/reschedule/", TaskRescheduleView.as_view(), name="reschedule_task"),
    path("schedule/", ScheduleListView.as_view(), name="schedule_list"),
    path("schedule/add/", ScheduleCreateView.as_view(), name="add_schedule"),
    path("schedule/<slug:pk>/", ScheduleDetailView.as_view(), name="schedule_detail"),
    path("schedule/<slug:pk>/edit/", ScheduleUpdateView.as_view(), name="edit_schedule"),
    path("schedule/<slug:pk>/delete/", ScheduleDeleteView.as_view(), name="delete_schedule"),
    path("schedule/<slug:schedule_id>/run/", ScheduleRunView.as_view(), name="run_schedule"),
]
