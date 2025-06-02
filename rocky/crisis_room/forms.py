import json
from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.http.request import QueryDict
from django.utils.translation import gettext_lazy as _
from tools.forms.base import BaseRockyForm

from crisis_room.models import Dashboard, DashboardItem


class AddDashboardForm(BaseRockyForm):
    dashboard_name = forms.CharField(label=_("Name"), required=True)


class AddDashboardItemForm(BaseRockyForm):
    dashboard = forms.ChoiceField(required=True, widget=forms.Select, choices=[])

    title = forms.CharField(label=_("Title on dashboard"), required=True)

    limit = forms.ChoiceField(
        label=_("Number of rows in list"),
        required=True,
        widget=forms.Select,
        choices=([("5", "5"), ("10", "10"), ("15", "15"), ("20", "20"), ("30", "30")]),
        initial="20",
    )

    size = forms.ChoiceField(
        label=_("Dashboard item size"),
        required=True,
        widget=forms.RadioSelect(),
        choices=(("1", _("Full width")), ("2", _("Half width"))),
        initial="1",
    )

    def __init__(self, organization, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.fields["dashboard"].choices = self.get_dashboard_selection()
        self.recipe_id = None
        self.query_from = ""
        self.template = ""
        self.display_in_dashboard = True
        self.data: QueryDict = kwargs.pop("data")

    def get_dashboard_selection(self) -> list[tuple[str, str]]:
        default = [("", "--- Select an option ----")]
        dashboards = [
            (dashboard.id, dashboard.name)
            for dashboard in Dashboard.objects.filter(organization=self.organization).exclude(
                dashboarditem__findings_dashboard=True
            )
        ]
        return default + dashboards

    def get_dashboard(self) -> Dashboard | None:
        try:
            dashboard_id = self.cleaned_data.get("dashboard", "")
            return Dashboard.objects.get(id=dashboard_id, organization=self.organization)
        except Dashboard.DoesNotExist:
            raise ValidationError("Dashboard does not exist.")
        except ValueError:
            raise ValidationError("No Dashboard selected. Choose an option from the list.")

    def has_duplicate_name(self, dashboard: Dashboard, title_dashboard_item: str) -> bool:
        return DashboardItem.objects.filter(dashboard=dashboard, name=title_dashboard_item).exists()

    def get_settings(self) -> dict[str, Any]:
        column_values = self.data.getlist("column_values", [])
        column_names = self.data.getlist("column_names", [])
        columns = dict(zip(column_values, column_names))

        if not columns:
            raise ValidationError("Please choose at least one column.")

        size = self.cleaned_data.get("size", "1")

        return {"size": size, "columns": columns}

    def get_query(self) -> dict[str, Any]:
        sort_by = self.cleaned_data.get("order_by", "").split("-", 1)

        order_by = sort_by[0]
        sorting_order = sort_by[1]
        limit = int(self.cleaned_data.get("limit", 10))

        return {"order_by": order_by, "asc_desc": sorting_order, "limit": limit}

    def create_dashboard_item(self) -> None:
        dashboard = self.get_dashboard()
        title = self.cleaned_data.get("title", "")

        dashboard_item = {
            "dashboard": dashboard,
            "name": title,
            "recipe": self.recipe_id,
            "query_from": self.query_from,
            "query": json.dumps(self.get_query()),
            "template": self.template,
            "settings": self.get_settings(),
            "display_in_dashboard": self.display_in_dashboard,
        }

        try:
            DashboardItem.objects.create(**dashboard_item)
        except IntegrityError:
            raise ValidationError(_("An error occurred while adding dashboard item."))

    def clean_dashboard(self):
        dashboard_name = self.cleaned_data.get("dashboard", "")
        self.get_dashboard()
        return dashboard_name

    def clean_title(self):
        title = self.cleaned_data.get("title", "")
        dashboard = self.get_dashboard()
        if dashboard is not None and self.has_duplicate_name(dashboard, title):
            raise ValidationError("An item with that name already exists. Try a different title.")
        return title

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        self.create_dashboard_item()
        return cleaned_data


class AddObjectListDashboardItemForm(AddDashboardItemForm):
    order_by = forms.ChoiceField(
        label=_("List sorting by"),
        required=True,
        widget=forms.Select,
        choices=(
            ("object_type-asc", _("Type (A-Z)")),
            ("object_type-desc", _("Type (Z-A)")),
            ("scan_level-asc", _("Clearance level (Low-High)")),
            ("scan_level-desc", _("Clearance level (High-Low)")),
        ),
    )

    def __init__(self, organization, *args, **kwargs):
        super().__init__(organization, *args, **kwargs)
        self.query_from = "object_list"
        self.template = "partials/dashboard_ooi_list.html"

    def get_query(self):
        default_query = super().get_query()

        ooi_types = self.data.getlist("ooi_type", [])
        clearance_level = self.data.getlist("clearance_level", [])
        clearance_type = self.data.getlist("clearance_type", [])
        search_string = self.data.get("search_string")

        query = {
            "ooi_types": ooi_types,
            "scan_level": clearance_level,
            "scan_profile_type": clearance_type,
            "search_string": search_string,
        }
        return default_query | query


class AddFindingListDashboardItemForm(AddDashboardItemForm):
    order_by = forms.ChoiceField(
        label=_("List sorting by"),
        required=True,
        widget=forms.Select,
        choices=(
            ("score-asc", _("Severity (Low-High)")),
            ("score-desc", _("Severity (High-Low)")),
            ("finding_type-asc", _("Finding (A-Z)")),
            ("finding_type-desc", _("Finding (Z-A)")),
        ),
    )

    def __init__(self, organization, *args, **kwargs):
        super().__init__(organization, *args, **kwargs)
        self.query_from = "finding_list"
        self.template = "partials/dashboard_finding_list.html"

    def get_query(self):
        default_query = super().get_query()

        severities = self.data.getlist("severity", [])
        muted_findings = self.data.get("muted_findings", "non-muted")
        exclude_muted = muted_findings == "non-muted"
        only_muted = muted_findings == "muted"
        search_string = self.data.get("search_string")

        query = {
            "severities": severities,
            "exclude_muted": exclude_muted,
            "only_muted": only_muted,
            "search_string": search_string,
        }

        return default_query | query
