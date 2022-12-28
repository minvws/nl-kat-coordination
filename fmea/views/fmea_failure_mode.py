from typing import List, Dict

from django.contrib import messages
from django.urls.base import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView
from fmea.models import FailureMode, FailureModeEffect
from django.views.generic.list import ListView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from fmea.forms import FailureModeForm
from fmea.views.view_helpers import FailureModeBreadcrumbsMixin


@class_view_decorator(otp_required)
class FailureModeCreateView(FailureModeBreadcrumbsMixin, CreateView):
    """
    Create a new failure mode with the failure mode form of FMEA.
    """

    model = FailureMode
    template_name = "fmea/fmea_failure_mode_form.html"
    form_class = FailureModeForm

    def get_success_url(self, **kwargs):
        return reverse_lazy("fmea_failure_mode_detail", kwargs={"pk": self.object.id})

    def form_valid(self, form):
        self.add_success_notification()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["failure_mode_effect_exist"] = FailureModeEffect.objects.count() > 0
        return context

    def add_success_notification(self):
        success_message = _("Failure mode succesfully created.")
        messages.add_message(self.request, messages.SUCCESS, success_message)

    def build_breadcrumbs(self) -> List[Dict[str, str]]:
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append(
            {
                "text": _("Create"),
                "url": reverse("fmea_failure_mode_create"),
            }
        )

        return breadcrumbs


@class_view_decorator(otp_required)
class FailureModeListView(FailureModeBreadcrumbsMixin, ListView):
    """
    View of all failure modes.
    """

    template_name = "fmea/fmea_failure_mode_list.html"
    model = FailureMode
    paginate_by = 10


@class_view_decorator(otp_required)
class FailureModeUpdateView(FailureModeBreadcrumbsMixin, UpdateView):
    model = FailureMode
    form_class = FailureModeForm
    template_name = "fmea/fmea_failure_mode_form.html"

    def get_success_url(self, **kwargs):
        return reverse_lazy("fmea_failure_mode_detail", kwargs={"pk": self.object.id})

    def build_breadcrumbs(self) -> List[Dict[str, str]]:
        breadcrumbs = super().build_breadcrumbs()

        breadcrumbs.append(
            {
                "text": self.object.failure_mode,
                "url": reverse("fmea_failure_mode_detail", kwargs={"pk": self.kwargs["pk"]}),
            }
        )
        breadcrumbs.append(
            {
                "text": _("Edit"),
                "url": reverse(
                    "fmea_failure_mode_update",
                    kwargs={"pk": self.kwargs["pk"]},
                ),
            }
        )

        return breadcrumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["editing_view"] = "editing"
        context["failure_mode_effect_exist"] = FailureModeEffect.objects.count() > 0
        return context


@class_view_decorator(otp_required)
class FailureModeDetailView(FailureModeBreadcrumbsMixin, DetailView):
    """
    View for 1 failure mode. Get failure mode with ID # in URL
    """

    template_name = "fmea/fmea_failure_mode_detail.html"
    model = FailureMode

    def build_breadcrumbs(self) -> List[Dict[str, str]]:
        breadcrumbs = super().build_breadcrumbs()

        breadcrumbs.append(
            {
                "text": self.object.failure_mode,
                "url": reverse("fmea_failure_mode_detail", kwargs={"pk": self.kwargs["pk"]}),
            }
        )

        return breadcrumbs
