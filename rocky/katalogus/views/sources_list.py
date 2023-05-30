from django.views.generic import ListView

from katalogus.models import Source


class SourceListView(ListView):
    model = Source
    template_name = "sources_list.html"
    context_object_name = "sources"
