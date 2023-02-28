from typing import List, Dict

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls.base import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from fmea.forms import FailureModeAffectedObjectForm
from fmea.models import FailureMode, FailureModeAffectedObject, FailureModeTreeObject
from fmea.views.view_helpers import AffectedObjectBreadcrumbsMixin


@class_view_decorator(otp_required)
class FailureModeAffectedObjectCreateView(AffectedObjectBreadcrumbsMixin, CreateView):
    """
    View of failure modes with the affected departments.
    """

    model = FailureModeAffectedObject
    template_name = "fmea/fmea_failure_mode_affected_object_form.html"
    form_class = FailureModeAffectedObjectForm

    def get_success_url(self, **kwargs):
        return reverse_lazy("fmea_failure_mode_affected_object_detail", kwargs={"pk": self.object.id})

    def form_valid(self, form):
        self.add_success_notification()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["failure_mode_exist"] = FailureMode.objects.all().exists()
        return context

    def add_success_notification(self):
        success_message = _("Failure mode affected objects succesfully created.")
        messages.add_message(self.request, messages.SUCCESS, success_message)

    def build_breadcrumbs(self) -> List[Dict[str, str]]:
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append(
            {
                "text": _("Create"),
                "url": reverse("fmea_failure_mode_affected_object_create"),
            }
        )

        return breadcrumbs


@class_view_decorator(otp_required)
class FailureModeAffectedObjectUpdateView(AffectedObjectBreadcrumbsMixin, UpdateView):
    model = FailureModeAffectedObject
    form_class = FailureModeAffectedObjectForm
    template_name = "fmea/fmea_failure_mode_affected_object_form.html"
    success_url = reverse_lazy("fmea_failure_mode_affected_object_list")

    def get_object(self, *args, **kwargs):
        failure_mode_affected_objects = get_object_or_404(self.model, pk=self.kwargs["pk"])
        return failure_mode_affected_objects

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["editing_view"] = "editing"
        context["id"] = self.kwargs["pk"]
        context["failure_mode_exist"] = FailureMode.objects.all().exists()
        return context

    def build_breadcrumbs(self) -> List[Dict[str, str]]:
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append(
            {
                "text": self.object.failure_mode,
                "url": reverse(
                    "fmea_failure_mode_affected_object_detail",
                    kwargs={"pk": self.kwargs["pk"]},
                ),
            }
        )
        breadcrumbs.append(
            {
                "text": _("Edit"),
                "url": reverse(
                    "fmea_failure_mode_affected_object_update",
                    kwargs={"pk": self.kwargs["pk"]},
                ),
            }
        )

        return breadcrumbs


@class_view_decorator(otp_required)
class FailureModeAffectedObjectListView(AffectedObjectBreadcrumbsMixin, ListView):
    """
    View of all failure modes affected objects.
    """

    template_name = "fmea/fmea_failure_mode_affected_object_list.html"
    model = FailureModeAffectedObject
    paginate_by = 10


@class_view_decorator(otp_required)
class FailureModeAffectedObjectDetailView(AffectedObjectBreadcrumbsMixin, DetailView):
    """
    View for 1 failure mode affected objects.
    """

    template_name = "fmea/fmea_failure_mode_affected_object_detail.html"
    model = FailureModeAffectedObject


@class_view_decorator(otp_required)
class FMEATreeObjectView(View):
    """
    Add tree nodes to affected departments
    """

    def post(self, request, *args, **kwargs):
        graph_url = request.POST["current-url"]
        self.create_objects(request)
        return redirect(graph_url)

    def create_objects(self, request):
        department = request.POST["department"]
        selected_oois = request.POST.getlist("selected_ooi")
        if department and selected_oois:
            for selected_ooi in selected_oois:
                try:
                    fmea_tree_object = FailureModeTreeObject(tree_object=selected_ooi, affected_department=department)
                    fmea_tree_object.save()
                except ValidationError:
                    self.add_error_notification()
                    return
            self.add_success_notification()
        else:
            self.add_error_notification()

    def add_success_notification(self):
        success_message = _("Treeobjects succesfully added.")
        messages.add_message(self.request, messages.SUCCESS, success_message)

    def add_error_notification(self):
        error_message = _("Please select a department or ooi.")
        messages.add_message(self.request, messages.ERROR, error_message)
