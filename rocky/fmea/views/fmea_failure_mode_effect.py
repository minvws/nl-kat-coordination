from django.contrib import messages
from django.urls.base import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView
from tools.view_helpers import Breadcrumb

from fmea.forms import FailureModeEffectForm
from fmea.models import FailureModeEffect
from fmea.views.view_helpers import FailureModeEffectBreadcrumbsMixin


class FailureModeEffectCreateView(FailureModeEffectBreadcrumbsMixin, CreateView):
    """
    View to create a failure mode effect.
    """

    model = FailureModeEffect
    template_name = "fmea/fmea_failure_mode_effect_form.html"
    form_class = FailureModeEffectForm

    def get_success_url(self, **kwargs):
        return reverse_lazy("fmea_failure_mode_effect_detail", kwargs={"pk": self.object.id})

    def form_valid(self, form):
        self.add_success_notification()
        return super().form_valid(form)

    def add_success_notification(self):
        success_message = _("Failure mode effect successfully created.")
        messages.add_message(self.request, messages.SUCCESS, success_message)

    def build_breadcrumbs(self) -> list[Breadcrumb]:
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append(
            {
                "text": _("Create"),
                "url": reverse("fmea_failure_mode_effect_create"),
            }
        )

        return breadcrumbs


class FailureModeEffectUpdateView(FailureModeEffectBreadcrumbsMixin, UpdateView):
    """
    View for updating a failure mode effect.
    """

    model = FailureModeEffect
    form_class = FailureModeEffectForm
    template_name = "fmea/fmea_failure_mode_effect_form.html"

    def get_success_url(self, **kwargs):
        return reverse_lazy("fmea_failure_mode_effect_detail", kwargs={"pk": self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["editing_view"] = "editing"
        return context

    def build_breadcrumbs(self) -> list[Breadcrumb]:
        breadcrumbs = super().build_breadcrumbs()

        breadcrumbs.append(
            {
                "text": self.object.effect,
                "url": reverse("fmea_failure_mode_effect_detail", kwargs={"pk": self.kwargs["pk"]}),
            }
        )
        breadcrumbs.append(
            {
                "text": _("Edit"),
                "url": reverse(
                    "fmea_failure_mode_effect_update",
                    kwargs={"pk": self.kwargs["pk"]},
                ),
            }
        )

        return breadcrumbs


class FailureModeEffectDetailView(FailureModeEffectBreadcrumbsMixin, DetailView):
    """
    View for 1 failure mode effect. id in kwargs.
    """

    template_name = "fmea/fmea_failure_mode_effect_detail.html"
    model = FailureModeEffect

    def build_breadcrumbs(self) -> list[Breadcrumb]:
        breadcrumbs = super().build_breadcrumbs()

        breadcrumbs.append(
            {
                "text": self.object.effect,
                "url": reverse("fmea_failure_mode_detail", kwargs={"pk": self.kwargs["pk"]}),
            }
        )

        return breadcrumbs


class FailureModeEffectListView(FailureModeEffectBreadcrumbsMixin, ListView):
    """
    View of all failure modes effects.
    """

    template_name = "fmea/fmea_failure_mode_effect_list.html"
    model = FailureModeEffect
    paginate_by = 10
