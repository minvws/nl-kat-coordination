from enum import Enum
from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import ProcessFormView


class PageActions(Enum):
    START_SCAN = "start_scan"
    SUBMIT_ANSWER = "submit_answer"
    RESCHEDULE_TASK = "reschedule_task"
    CHANGE_CLEARANCE_LEVEL = "change_clearance_level"
    SCAN_OOIS = "scan_oois"


class PageActionsView(ProcessFormView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.START_SCAN = PageActions.START_SCAN.value
        self.SUBMIT_ANSWER = PageActions.SUBMIT_ANSWER.value
        self.RESCHEDULE_TASK = PageActions.RESCHEDULE_TASK.value
        self.CHANGE_CLEARANCE_LEVEL = PageActions.CHANGE_CLEARANCE_LEVEL.value
        self.SCAN_OOIS = PageActions.SCAN_OOIS.value
        self.action = request.POST.get("action")

    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        if not self.action or self.action is None:
            messages.error(self.request, _("Could not process your request, action required."))

        return self.get(request, *args, **kwargs)
