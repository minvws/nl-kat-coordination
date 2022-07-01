import datetime
from typing import Dict, Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django_otp.decorators import otp_required
from django.utils.translation import gettext_lazy as _
from octopoes.models import Reference

from rocky.flower import FlowerClient, FlowerException
from rocky.settings import FLOWER_API
from tools.models import Job

TASKS_LIMIT = 30


@otp_required
def task_list(request: HttpRequest) -> HttpResponse:
    boefjes: Dict[str, Any] = {}
    context = {
        "breadcrumb_list": [
            {"url": reverse("ooi_list"), "text": _("Objects")},
            {"url": reverse("task_list"), "text": _("Tasks")},
        ],
        "tasks": boefjes,
    }
    flower = FlowerClient(FLOWER_API)

    try:
        tasks = flower.get_tasks("tasks.handle_boefje", limit=TASKS_LIMIT)

        # for task_id, task in tasks.items():
        #     boefjes[task_id] = {
        #         "boefje": task_id,
        #         # "input_ooi": Reference.from_str(job.input_ooi)
        #         # if job.input_ooi
        #         # else None,
        #         # **_parse_meta(tasks[job_id]),
        #     }

        jobs = (
            Job.objects.filter(
                id__in=tasks.keys(), organization=request.active_organization
            )
            .order_by("-created")
            .all()
        )

        for job in jobs:
            job_id = str(job.id)
            boefjes[job_id] = {
                "boefje": job.boefje_id,
                "input_ooi": Reference.from_str(job.input_ooi)
                if job.input_ooi
                else None,
                **_parse_meta(tasks[job_id]),
            }

    # todo: fix using generic error views
    except FlowerException as ex:
        context["error"] = ex

    return render(request, "tasks/list.html", context)


def _parse_meta(meta: Dict) -> Dict:
    # The states
    # 'received' PENDING (waiting for execution or unknown task id)
    # 'started' STARTED (task has been started)
    # 'succeeded' SUCCESS (task executed successfully)
    # 'failed' FAILURE (task execution resulted in exception)

    new_meta = {"id": meta["uuid"], "state": meta["state"]}
    for state in ["received", "started", "succeeded", "failed"]:
        time = meta.get(state)
        if time is not None:
            time = datetime.datetime.utcfromtimestamp(time)
        new_meta[state] = time

    return new_meta
