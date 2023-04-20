from enum import Enum

from django.contrib import messages
from requests.exceptions import RequestException

from rocky.views.ooi_detail import OOIDetailView


class PageActions(Enum):
    ANSWER_QUESTION = "answer_question"


class QuestionDetailView(OOIDetailView):
    template_name = "oois/question_detail.html"

    def post(self, request, *args, **kwargs):
        if not self.indemnification_present:
            messages.add_message(
                request, messages.ERROR, f"Indemnification not present at organization {self.organization}."
            )
            return self.get(request, status_code=403, *args, **kwargs)

        if "action" not in self.request.POST:
            return self.get(request, status_code=404, *args, **kwargs)

        self.ooi = self.get_ooi()

        action = self.request.POST.get("action")
        if not self.handle_page_action(action):
            return self.get(request, status_code=500, *args, **kwargs)

        success_message = "Successfully answered question."  # TODO: abstract?
        messages.add_message(request, messages.SUCCESS, success_message)

        return self.get(request, *args, **kwargs)

    def handle_page_action(self, action: str) -> bool:
        try:
            if action == PageActions.ANSWER_QUESTION.value:
                # TODO: save answer to Bytes
                return True

        except RequestException as exception:
            messages.add_message(self.request, messages.ERROR, f"{action} failed: '{exception}'")

