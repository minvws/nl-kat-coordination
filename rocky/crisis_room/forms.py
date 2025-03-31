from django import forms
from django.utils.translation import gettext_lazy as _
from tools.forms.base import BaseRockyForm


class SelectDashboardForm(BaseRockyForm):
    dashboard = forms.ChoiceField(required=True, widget=forms.Select, choices=[])


class ObjectListSettingsForm(BaseRockyForm):
    report_name = forms.CharField(label=_("Title on dashboard"), required=True)

    sorting_by = forms.ChoiceField(
        label=_("List sorting by"),
        required=True,
        widget=forms.Select,
        choices=([("type", _("Type")), ("clearance_level", _("Clearance level"))]),
    )

    limit = forms.ChoiceField(
        label=_("Number of objects in list"),
        required=True,
        widget=forms.Select,
        choices=([("5", "5"), ("10", "10"), ("15", "15"), ("20", "20"), ("30", "30")]),
        initial="20",
    )

    columns = forms.MultipleChoiceField(
        label=_("Show table columns"), required=True, widget=forms.CheckboxSelectMultiple
    )

    size = forms.ChoiceField(
        label=_("Dashboard item size"),
        required=True,
        widget=forms.RadioSelect(attrs={"class": "submit-on-click"}),
        choices=(("name", _("Object name")), ("type", _("Type")), ("clearance_level", _("Clearance level"))),
        initial="type",
    )
