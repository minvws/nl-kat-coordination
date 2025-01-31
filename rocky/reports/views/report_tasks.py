from rocky.paginator import RockyPaginator
from rocky.views.page_actions import PageActionsView
from rocky.views.scheduler import SchedulerView
from rocky.views.tasks import SchedulerListView


class ReportTaskListView(SchedulerView, SchedulerListView, PageActionsView):
    template_name = "tasks/report_task_list.html"
    paginator_class = RockyPaginator
    paginate_by = 50
    context_object_name = "report_task_list"
    task_type = "report"

    def get_queryset(self):
        return self.get_task_list()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_report_tasks"] = len(self.object_list)
        return context
