import json
from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.http.request import QueryDict
from django.utils.translation import gettext_lazy as _
from tools.forms.base import BaseRockyForm

from crisis_room.models import FINDINGS_DASHBOARD_NAME, Dashboard, DashboardItem
from rocky.views.mixins import FINDING_LIST_COLUMNS, OBJECT_LIST_COLUMNS


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
        self.table_columns = {}
        self.data: QueryDict = kwargs.pop("data")

    def clean_title(self):
        """Checks if title is already used as dashboard item name"""
        name = self.cleaned_data.get("title")
        dashboard = self.cleaned_data.get("dashboard")
        if dashboard is not None and self.has_duplicate_name(dashboard, name):
            raise ValidationError(_("An item with that name already exists. Try a different title."))
        return name

    def clean_columns(self):
        column_values = self.cleaned_data.get("columns", [])
        columns = [
            {column_value: str(self.table_columns.get(column_value))}
            for column_value in column_values
            if column_value in self.table_columns
        ]
        return columns

    def clean(self):
        cleaned_data = super().clean()
        # clean all form data and dashboard item creation
        if self.data:
            self.create_dashboard_item()
        return cleaned_data

    def get_dashboard(self) -> Dashboard | None:
        try:
            dashboard_id = self.cleaned_data.get("dashboard")
            return Dashboard.objects.get(id=dashboard_id, organization=self.organization)
        except Dashboard.DoesNotExist:
            raise ValidationError("Dashboard does not exist.")
        except ValueError:
            raise ValidationError("No Dashboard selected. Choose an option from the list.")

    def get_dashboard_selection(self) -> list[tuple[str, str]]:
        default = [("", "--- Select an option ----")]
        dashboards = Dashboard.objects.filter(organization=self.organization).exclude(name=FINDINGS_DASHBOARD_NAME)
        dashboard_choices = [(dashboard.id, dashboard.name) for dashboard in dashboards]

        return default + dashboard_choices

    def has_duplicate_name(self, dashboard: Dashboard, name: str | None) -> bool:
        return DashboardItem.objects.filter(dashboard=dashboard, name=name).exists()

    def get_query(self) -> dict[str, Any]:
        sort_by = self.cleaned_data.get("order_by", "").split("-", 1)

        order_by = sort_by[0]
        sorting_order = sort_by[1]
        limit = int(self.cleaned_data.get("limit", 10))
        observed_at = self.data.get("observed_at")
        search = self.data.get("search", "")

        return {
            "observed_at": observed_at,
            "order_by": order_by,
            "sorting_order": sorting_order,
            "limit": limit,
            "search": search,
        }

    def get_settings(self) -> dict[str, Any]:
        size = self.cleaned_data.get("size", "1")
        columns = self.cleaned_data.get("columns", [])

        return {"size": size, "columns": columns}

    def create_dashboard_item(self) -> None:
        dashboard = self.get_dashboard()
        name = self.cleaned_data.get("title")
        if dashboard is not None and name is not None:
            try:
                form_data = {
                    "dashboard": dashboard,
                    "name": name,
                    "recipe": self.recipe_id,
                    "query_from": self.query_from,
                    "query": json.dumps(self.get_query()),
                    "template": self.template,
                    "settings": self.get_settings(),
                    "display_in_dashboard": self.display_in_dashboard,
                }
                DashboardItem.objects.create(**form_data)
            except ValidationError as error:
                raise ValidationError(error)
            except IntegrityError:
                raise ValidationError(_("An error occurred while adding dashboard item."))


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
    columns = forms.MultipleChoiceField(
        label=_("Show table columns"),
        required=True,
        widget=forms.CheckboxSelectMultiple(attrs={"checked": True}),
        choices=((value, name) for value, name in OBJECT_LIST_COLUMNS.items()),
    )

    def __init__(self, organization, *args, **kwargs):
        super().__init__(organization, *args, **kwargs)
        self.query_from = "object_list"
        self.template = "partials/dashboard_ooi_list.html"
        self.table_columns = OBJECT_LIST_COLUMNS

    def get_query(self):
        default_query = super().get_query()

        query = {
            "ooi_type": self.data.getlist("ooi_type", []),
            "clearance_level": self.data.getlist("clearance_level", []),
            "clearance_type": self.data.getlist("clearance_type", []),
            "search": self.data.get("search_string", ""),
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

    columns = forms.MultipleChoiceField(
        label=_("Show table columns"),
        required=True,
        widget=forms.CheckboxSelectMultiple(attrs={"checked": True}),
        choices=((value, name) for value, name in FINDING_LIST_COLUMNS.items()),
    )

    def __init__(self, organization, *args, **kwargs):
        super().__init__(organization, *args, **kwargs)
        self.query_from = "finding_list"
        self.template = "partials/dashboard_finding_list.html"
        self.table_columns = FINDING_LIST_COLUMNS

    def get_query(self):
        default_query = super().get_query()

        severities = self.data.getlist("severity", [])
        muted_findings = self.data.get("muted_findings", "non-muted")

        query = {"severity": severities, "muted_findings": muted_findings}

        return default_query | query
