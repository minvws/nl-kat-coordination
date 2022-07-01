from django.urls.base import reverse_lazy
from django.utils.translation import gettext_lazy as _
from rocky.views.ooi_view import BaseDeleteOOIView
from tools.view_helpers import get_ooi_url


class OOIDeleteView(BaseDeleteOOIView):
    template_name = "oois/ooi_delete.html"
    success_url = reverse_lazy("ooi_list")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.ooi = self.get_ooi()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Construct breadcrumbs
        breadcrumb_list = self.get_breadcrumb_list()
        breadcrumb_list.append(
            {
                "url": get_ooi_url("ooi_delete", self.ooi.primary_key),
                "text": _("Delete"),
            }
        )

        context["ooi"] = self.ooi
        context["props"] = self.ooi.dict()
        context["breadcrumbs"] = breadcrumb_list

        return context
