from typing import List

from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from requests import HTTPError
from tools.forms.ooi import OoiTreeSettingsForm
from tools.ooi_helpers import create_object_tree_item_from_ref, filter_ooi_tree, get_ooi_types_from_tree, hydrate_tree
from tools.view_helpers import Breadcrumb, get_ooi_url

from rocky.views.ooi_view import BaseOOIDetailView


class OOITreeView(BaseOOIDetailView):
    template_name = "oois/ooi_tree.html"
    connector_form_class = OoiTreeSettingsForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.ooi_id = self.request.GET.get("ooi_id", "")
        self.observed_at = self.get_observed_at()
        self.depth = self.get_depth()
        self.filtered_types = self.request.GET.getlist("ooi_type", [])
        self.view = self.request.GET.get("view", "condensed")

        try:
            self.tree = self.get_ooi_tree(self.ooi_id, self.depth, self.observed_at)
            self.tree_objects = create_object_tree_item_from_ref(self.tree.root, self.tree.store)
            self.ooi_types = get_ooi_types_from_tree(self.tree_objects, False)
            self.filtered_tree_objects = filter_ooi_tree(self.tree_objects, self.filtered_types)
            self.hydrated_tree = hydrate_tree(self.filtered_tree_objects, self.organization.code)
        except HTTPError:
            messages.error(request, _("We could not process your request."))

    def get_connector_form_kwargs(self):
        kwargs = {
            "initial": {"ooi_type": self.ooi_types},
            "ooi_types": self.ooi_types,
        }

        if "observed_at" in self.request.GET:
            kwargs.update({"data": self.request.GET})
        return kwargs

    def build_breadcrumbs(self) -> List[Breadcrumb]:
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append(self.get_last_breadcrumb())
        return breadcrumbs

    def get_last_breadcrumb(self):
        return {
            "url": get_ooi_url("ooi_tree", self.ooi.primary_key, self.organization.code),
            "text": _("Tree Visualisation"),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["tree"] = self.filtered_tree_objects
        context["tree_view"] = self.view
        context["observed_at_form"] = self.get_connector_form()

        return context


class OOISummaryView(OOITreeView):
    template_name = "oois/ooi_summary.html"

    def get_last_breadcrumb(self):
        return {
            "url": get_ooi_url("ooi_summary", self.ooi.primary_key, self.organization.code),
            "text": _("Summary"),
        }


class OOIGraphView(OOITreeView):
    template_name = "graph-d3.html"

    def get_last_breadcrumb(self):
        return {
            "url": get_ooi_url("ooi_graph", self.ooi.primary_key, self.organization.code),
            "text": _("Graph Visualisation"),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tree"] = self.hydrated_tree
        return context
