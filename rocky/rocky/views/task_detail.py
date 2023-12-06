from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from katalogus.views.mixins import BoefjeMixin, NormalizerMixin

from rocky.scheduler import client
from rocky.views.mixins import OctopoesView


class TaskDetailView(OctopoesView, TemplateView):
    def get_task(self, task_id):
        task = client.get_task_details(self.organization.code, task_id)
        if task:
            return task
        else:
            messages.add_message(self.request, messages.ERROR, _("Task could not be found."))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["task_id"] = kwargs["task_id"]
        context["task"] = self.get_task(context["task_id"])
        return context


class BoefjeTaskDetailView(BoefjeMixin, TaskDetailView):
    template_name = "tasks/boefje_task_detail.html"
    plugin_type = "boefje"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["breadcrumbs"] = [
            {
                "url": reverse("task_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Tasks"),
            },
            {
                "url": reverse(
                    "boefje_task_view",
                    kwargs={"organization_code": self.organization.code, "task_id": context["task_id"]},
                ),
                "text": context["task"].p_item.data.boefje.id,
            },
        ]

        return context


class NormalizerTaskJSONView(NormalizerMixin, TaskDetailView):
    plugin_type = "normalizer"

    def get_output_oois(self, task):
        try:
            return self.octopoes_api_connector.list_origins(
                valid_time=task.p_item.data.raw_data.boefje_meta.ended_at, task_id=task.id
            )[0].result
        except IndexError:
            return []

    def get(self, request, *args, **kwargs):
        task_id = kwargs["task_id"]
        task = self.get_task(task_id)
        return JsonResponse(
            {
                "oois": self.get_output_oois(task),
                "valid_time": task.p_item.data.raw_data.boefje_meta.ended_at.strftime("%Y-%m-%dT%H:%M:%S"),
            },
            safe=False,
        )
