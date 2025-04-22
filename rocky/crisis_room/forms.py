from django import forms
from django.utils.translation import gettext_lazy as _
from tools.forms.base import BaseRockyForm
from tools.models import Organization

from crisis_room.management.commands.dashboards import FINDINGS_DASHBOARD_NAME
from crisis_room.models import Dashboard


class AddDashboardForm(BaseRockyForm):
    dashboard_name = forms.CharField(label=_("Name"), required=True)


class ObjectListSettingsForm(BaseRockyForm):
    dashboard = forms.ChoiceField(required=True, widget=forms.Select, choices=[])

    title = forms.CharField(label=_("Title on dashboard"), required=True)

    order_by = forms.ChoiceField(
        label=_("List sorting by"),
        required=True,
        widget=forms.Select,
        choices=(
            [
                ("object_type-asc", _("Type (A-Z)")),
                ("object_type-desc", _("Type (Z-A)")),
                ("scan_level-asc", _("Clearance level (High-Low)")),
                ("scan_level-desc", _("Clearance level (Low-High)")),
            ]
        ),
    )

    limit = forms.ChoiceField(
        label=_("Number of objects in list"),
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

    def __init__(self, *args, organization, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["dashboard"].choices = self.get_dashboard_selection(organization)

    @staticmethod
    def get_dashboard_selection(organization: Organization) -> list[tuple[str, str]]:
        return [
            (dashboard.name, dashboard.name)
            for dashboard in Dashboard.objects.filter(organization=organization).exclude(name=FINDINGS_DASHBOARD_NAME)
        ]
