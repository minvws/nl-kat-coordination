from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView

from files.models import File
import structlog


logger = structlog.get_logger(__name__)


class FileListView(ListView):
    template_name = "file_list.html"
    model = File
    ordering = ["-id"]
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE

    def get_queryset(self):
        qs = super().get_queryset()

        if "task_id" in self.request.GET:
            qs = qs.filter(task_result__task__id=self.request.GET["task_id"])

        if "organization" in self.request.GET:
            qs = qs.filter(task_result__task__organization=self.request.GET["organization"])

        if "plugin_id" in self.request.GET:
            qs = qs.filter(task_result__task__data__plugin_id=self.request.GET["plugin_id"])

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("file_list"), "text": _("Files")}]

        return context


class FileCreateView(CreateView):
    model = File
    fields = ["file"]
    template_name = "file_form.html"

    def form_invalid(self, form):
        logger.error("Failed creating file", errors=form.errors)
        return redirect(reverse("file_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("file_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("file_list"), "text": _("Files")}]

        return context
