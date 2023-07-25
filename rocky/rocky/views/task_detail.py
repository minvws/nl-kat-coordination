import uuid

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from katalogus.views.mixins import BoefjeMixin, NormalizerMixin

from rocky.scheduler import client
from rocky.views.mixins import OctopoesView


class TaskDetailView(OctopoesView, TemplateView):
    @staticmethod
    def get_task(task_id):
        return client.get_task_details(task_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["task_id"] = uuid.UUID(kwargs["task_id"]).hex
        context["task"] = self.get_task(context["task_id"])
        context["breadcrumbs"] = [
            {"url": reverse("task_list", kwargs={"organization_code": self.organization.code}), "text": _("Tasks")},
        ]
        return context


class BoefjesTaskDetailView(BoefjeMixin, TaskDetailView):
    template_name = "tasks/boefje_task_detail.html"
    plugin_type = "boefje"


class NormalizerTaskDetailView(NormalizerMixin, TaskDetailView):
    template_name = "tasks/normalizer_task_detail.html"
    plugin_type = "normalizer"

    def get_output_oois(self, task):
        try:
            return self.octopoes_api_connector.list_origins(
                valid_time=task.p_item.data.raw_data.boefje_meta.ended_at, task_id=uuid.UUID(task.id).hex
            )[0].result
        except IndexError:
            return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["output_oois"] = self.get_output_oois(context["task"])
        return context
