from django.utils.translation import gettext_lazy as _
from octopoes.models import Reference

from rocky.views.ooi_view import BaseOOIFormView
from tools.view_helpers import get_ooi_url


class OOIEditView(BaseOOIFormView):
    template_name = "oois/ooi_edit.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.ooi = self.get_ooi()
        self.ooi_class = self.get_ooi_class()

    def get_initial(self):
        initial = super().get_initial()

        for attr, value in self.ooi:
            if isinstance(value, Reference):
                initial[attr] = str(value)
            elif isinstance(value, list):
                initial[attr] = [str(x) for x in value]
            else:
                initial[attr] = value

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Construct breadcrumbs
        breadcrumb_list = self.get_breadcrumb_list()
        breadcrumb_list.append(
            {
                "url": get_ooi_url("ooi_edit", self.ooi.primary_key),
                "text": _("Edit"),
            }
        )

        context["type"] = self.ooi_class.get_ooi_type()
        context["breadcrumbs"] = breadcrumb_list

        return context
