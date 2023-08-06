import uuid

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
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


class NormalizerTaskDetailView(NormalizerMixin, TaskDetailView):
    plugin_type = "normalizer"

    def get_output_oois(self, task):
        try:
            return self.octopoes_api_connector.list_origins(
                valid_time=task.p_item.data.raw_data.boefje_meta.ended_at, task_id=uuid.UUID(task.id).hex
            )[0].result
        except IndexError:
            return []

    def get(self, request, *args, **kwargs):
        task_id = uuid.UUID(kwargs["task_id"]).hex
        task = self.get_task(task_id)
        return JsonResponse(self.get_output_oois(task), safe=False)


class RescheduleTasksBulkView(NormalizerMixin, TaskDetailView):
    def post(self, request, *args, **kwargs):
        selected_tasks = request.POST.getlist("task", None)
        request.POST.get("reason", None)

        if not selected_tasks:
            return

        for task in selected_tasks:
            task_id = self.request.POST.get("task_id")
            task = client.get_task_details(task_id)

            new_id = (
                uuid.uuid4().hex
            )  # TODO: Consistent UUI-parsing across services https://github.com/minvws/nl-kat-coordination/issues/1451

            p_item = task.p_item
            p_item.id = new_id
            p_item.data.id = new_id

            client.push_task(f"{task.type}-{self.organization.code}", task.p_item)

            success_message = (
                "Your task is scheduled and will soon be started in the background. \n "
                "Results will be added to the object list when they are in. "
                "It may take some time, a refresh of the page may be needed to show the results."
            )
            messages.add_message(self.request, messages.SUCCESS, success_message)
            return

        return redirect(reverse("task_list", kwargs={"organization_code": self.organization.code}))
