from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView

from files.models import File


class FileListView(ListView):
    template_name = "file_list.html"
    model = File
    ordering = ["-id"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("file_list"), "text": _("Files")}]

        return context
