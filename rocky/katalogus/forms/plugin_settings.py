from typing import Dict

from django import forms
from django.utils.translation import gettext_lazy as _

FIELD_TYPES = {"string": forms.CharField, "integer": forms.IntegerField, "enum": forms.Select}
MAX_SETTINGS_VALUE_LENGTH = 128


class PluginSchemaForm(forms.Form):
    """This Form takes a plugin schema and turn all settings of schema into form fields."""

    error_messages = {
        "required": _("This field is required."),
    }

    def __init__(self, plugin_schema: Dict, values: Dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugin_schema = plugin_schema
        self.values = values
        self.populate_fields()

    def populate_fields(self):
        if not self.plugin_schema:
            return

        for field_name, field_props in self.plugin_schema["properties"].items():
            kwargs = {
                "required": field_name in self.plugin_schema["required"],
                "label": field_props.get("title", field_name),
                "help_text": _(field_props.get("description", "")),
                "error_messages": self.error_messages,
            }
            if field_props["type"] == "string":
                kwargs["max_length"] = min(
                    MAX_SETTINGS_VALUE_LENGTH, field_props.get("maxLength", MAX_SETTINGS_VALUE_LENGTH)
                )

            if field_name in self.values:
                kwargs["initial"] = self.values[field_name]

            field_type = FIELD_TYPES[field_props["type"]]
            self.fields[field_name] = field_type(**kwargs)

    def clean(self):
        # The form assigns null to all unfilled fields, but json-schema does not allow null for optional fields
        return {key: value for key, value in self.cleaned_data.items() if value is not None}
