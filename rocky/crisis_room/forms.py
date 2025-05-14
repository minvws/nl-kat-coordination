import json
from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.http.request import QueryDict
from django.utils.translation import gettext_lazy as _
from tools.forms.base import BaseRockyForm

from crisis_room.management.commands.dashboards import FINDINGS_DASHBOARD_NAME
from crisis_room.models import Dashboard, DashboardData


class AddDashboardForm(BaseRockyForm):
    dashboard_name = forms.CharField(label=_("Name"), required=True)


class ObjectListSettingsForm(BaseRockyForm):
    dashboard = forms.ChoiceField(required=True, widget=forms.Select, choices=[])

    title = forms.CharField(label=_("Title on dashboard"), required=True)

    order_by = forms.ChoiceField(label=_("List sorting by"), required=True, widget=forms.Select, choices=([]))

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

    def __init__(self, *args, organization, query_from, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.query_from = query_from
        self.fields["dashboard"].choices = self.get_dashboard_selection()
        self.fields["order_by"].choices = self.get_order_by_selection()

        data: QueryDict | None = kwargs.pop("data")

        if data:
            self.recipe_id = data.get("recipe_id")
            self.query_from = data.get("query_from")
            self.ooi_types = data.getlist("ooi_type", [])
            self.clearance_level = data.getlist("clearance_level", [])
            self.clearance_type = data.getlist("clearance_type", [])
            self.search_string = data.get("search_string")
            self.template = data.get("template")
            self.column_values = data.getlist("column_values", [])
            self.column_names = data.getlist("column_names", [])
            self.severities = data.getlist("severity", [])

            muted_findings = data.get("muted_findings", "non-muted")
            self.exclude_muted = muted_findings == "non-muted"
            self.only_muted = muted_findings == "muted"

    def clean_dashboard(self):
        dashboard_name = self.cleaned_data.get("dashboard", "")
        self.get_dashboard(dashboard_name)
        return dashboard_name

    def clean_title(self):
        title = self.cleaned_data.get("title", "")
        dashboard_name = self.cleaned_data.get("dashboard", "")
        dashboard = self.get_dashboard(dashboard_name)
        if dashboard is not None and self.has_duplicate_name(dashboard, title):
            raise ValidationError("An item with that name already exists. Try a different title.")
        return title

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        # Title is the only thing user really sets, the other values are prefilled which already contains data.
        title = self.cleaned_data.get("title", "")

        if title:
            self.create_dashboard_item(**cleaned_data)
        return cleaned_data

    def create_dashboard_item(self, **cleaned_data) -> None:
        dashboard = self.get_dashboard(cleaned_data.get("dashboard", ""))
        title = self.cleaned_data.get("title", None)

        sort_by = cleaned_data.get("order_by", "").split("-")
        order_by = sort_by[0]
        sorting_order = sort_by[1]

        limit = int(cleaned_data.get("limit", 10))
        size = cleaned_data.get("size", "1")

        query = None

        if self.query_from == "object_list":
            query = {
                "ooi_types": self.ooi_types,
                "scan_level": self.clearance_level,
                "scan_profile_type": self.clearance_type,
                "search_string": self.search_string,
                "order_by": order_by,
                "asc_desc": sorting_order,
                "limit": limit,
            }
        elif self.query_from == "finding_list":
            query = {
                "severities": self.severities,
                "exclude_muted": self.exclude_muted,
                "only_muted": self.only_muted,
                "search_string": self.search_string,
                "order_by": order_by,
                "asc_desc": sorting_order,
                "limit": limit,
            }

        columns = {column_value: self.column_names[index] for index, column_value in enumerate(self.column_values)}

        if not columns:
            raise ValidationError("Please choose at least one column.")

        settings = {"size": size, "columns": columns}

        dashboard_data = {
            "dashboard": dashboard,
            "name": title,
            "recipe": self.recipe_id if self.recipe_id else None,
            "query_from": self.query_from,
            "query": json.dumps(query),
            "template": self.template,
            "settings": settings,
            "display_in_dashboard": True,
        }

        try:
            DashboardData.objects.create(**dashboard_data)
        except IntegrityError:
            raise ValidationError(_("An error occurred while adding dashboard item."))

    def get_dashboard_selection(self) -> list[tuple[str, str]]:
        return [
            (dashboard.name, dashboard.name)
            for dashboard in Dashboard.objects.filter(organization=self.organization).exclude(
                name=FINDINGS_DASHBOARD_NAME
            )
        ]

    def get_order_by_selection(self) -> list[tuple[str, str]]:
        if self.query_from == "object_list":
            return [
                ("object_type-asc", _("Type (A-Z)")),
                ("object_type-desc", _("Type (Z-A)")),
                ("scan_level-asc", _("Clearance level (Low-High)")),
                ("scan_level-desc", _("Clearance level (High-Low)")),
            ]
        elif self.query_from == "finding_list":
            return [
                ("score-asc", _("Severity (Low-High)")),
                ("score-desc", _("Severity (High-Low)")),
                ("finding_type-asc", _("Finding (A-Z)")),
                ("finding_type-desc", _("Finding (Z-A)")),
            ]
        return []

    def get_dashboard(self, name: str) -> Dashboard | None:
        try:
            return Dashboard.objects.get(name=name, organization=self.organization)
        except Dashboard.DoesNotExist:
            raise ValidationError("Dashboard does not exist.")

    def has_duplicate_name(self, dashboard: Dashboard, title_dashboard_item: str) -> bool:
        return DashboardData.objects.filter(dashboard=dashboard, name=title_dashboard_item).exists()
