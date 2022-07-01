from typing import List

from django.utils.translation import gettext_lazy as _

from fmea.models import DEPARTMENTS
from rocky.views import BaseOOIDetailView
from rocky.views.ooi_view import OOIBreadcrumbsMixin
from tools.forms import OoiTreeSettingsForm
from tools.ooi_helpers import (
    get_ooi_types_from_tree,
    filter_ooi_tree,
    create_object_tree_item_from_ref,
)
from tools.view_helpers import get_ooi_url, Breadcrumb


class OOITreeView(OOIBreadcrumbsMixin, BaseOOIDetailView):
    template_name = "oois/ooi_tree.html"
    connector_form_class = OoiTreeSettingsForm

    def get_tree_dict(self):
        return create_object_tree_item_from_ref(self.tree.root, self.tree.store)

    def get_filtered_tree(self, tree_dict):
        filtered_types = self.request.GET.getlist("ooi_type", [])
        return filter_ooi_tree(tree_dict, filtered_types)

    def get_connector_form_kwargs(self):
        tree_dict = self.get_tree_dict()
        ooi_types = get_ooi_types_from_tree(tree_dict, False)

        kwargs = {
            "initial": {"ooi_type": ooi_types},
            "ooi_types": ooi_types,
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
            "url": get_ooi_url("ooi_tree", self.ooi.primary_key),
            "text": _("Tree Visualisation"),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["tree"] = self.get_filtered_tree(self.get_tree_dict())
        context["tree_view"] = self.request.GET.get("view", "condensed")
        context["observed_at_form"] = self.get_connector_form()

        return context

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.depth = self.get_depth()


class OOISummaryView(OOITreeView):
    template_name = "oois/ooi_summary.html"

    def get_last_breadcrumb(self):
        return {
            "url": get_ooi_url("ooi_summary", self.ooi.primary_key),
            "text": _("Summary"),
        }


class OOIGraphView(OOITreeView):
    template_name = "graph-d3.html"

    def get_filtered_tree(self, tree_dict):
        filtered_tree = super().get_filtered_tree(tree_dict)

        return hydrate_tree(filtered_tree)

    def get_last_breadcrumb(self):
        return {
            "url": get_ooi_url("ooi_graph", self.ooi.primary_key),
            "text": _("Graph Visualisation"),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["departments"] = DEPARTMENTS
        return context


def hydrate_tree(tree):
    return hydrate_branch(tree)


def hydrate_branch(branch):
    branch["name"] = branch["tree_meta"]["location"] + "-" + branch["ooi_type"]
    branch["overlay_data"] = {"Type": branch["ooi_type"]}
    if branch["ooi_type"] == "Finding":
        branch["overlay_data"]["Description"] = branch["description"]
        branch["overlay_data"]["Proof"] = branch["proof"]
    elif branch["ooi_type"] == "IpPort":
        branch["overlay_data"]["Port"] = str(branch["port"])
        branch["overlay_data"]["Protocol"] = branch["protocol"]
        branch["overlay_data"]["State"] = branch["state"]

    branch["display_name"] = branch["human_readable"]
    branch["graph_url"] = get_ooi_url("ooi_graph", branch["id"])

    if branch.get("children"):
        branch["children"] = [hydrate_branch(child) for child in branch["children"]]

    return branch
