from django_otp.decorators import otp_required
from requests import HTTPError
from two_factor.views.utils import class_view_decorator
from django.contrib import messages
from rocky.scheduler import SchedulerClient
from rocky.settings import SCHEDULER_API
from tools.models import Organization
from django.views.generic import TemplateView


scheduler_client = SchedulerClient(SCHEDULER_API)


@class_view_decorator(otp_required)
class TaskListView(TemplateView):
    template_name = "tasks/list.html"

    def dispatch(self, request, *args, **kwargs):
        org: Organization = request.active_organization
        self.boefje_task_response = None
        self.normalizer_task_response = None

        if org:
            try:
                self.boefje_task_response = scheduler_client.list_tasks(
                    f"boefje-{org.code}"
                )
                self.normalizer_task_response = scheduler_client.list_tasks(
                    f"normalizer-{org.code}"
                )
            except HTTPError:
                error_message = "Fetching tasks failed: no connection with scheduler"
                messages.add_message(self.request, messages.ERROR, error_message)
        else:
            error_message = "Organization could not be found"
            messages.add_message(self.request, messages.ERROR, error_message)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["boefje_task_response"] = self.boefje_task_response
        context["normalizer_task_response"] = self.normalizer_task_response
        return context
