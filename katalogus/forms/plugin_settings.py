from django import forms
from django.utils.translation import gettext_lazy as _


FIELD_TYPES = {"string": forms.CharField, "integer": forms.IntegerField, "enum": forms.Select}
MAX_SETTINGS_VALUE_LENGTH = 128


class PluginSchemaForm(forms.Form):
    """This Form takes a plugin schema and turn all settings of schema into form fields."""

    error_messages = {
        "required": _("This field is required."),
    }

    def __init__(self, plugin_schema, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugin_schema = plugin_schema
        self.populate_fields()

    def populate_fields(self):
        fields = self.plugin_schema["properties"]
        required_fields = self.plugin_schema["required"]
        help_text = ""
        for field_name, field_props in fields.items():
            field_type = FIELD_TYPES[field_props["type"]]
            if "description" in field_props:
                help_text = field_props["description"]
            kwargs = {
                "required": field_name in required_fields,
                "label": field_props.get("title", field_name),
                "help_text": _(help_text),
                "error_messages": self.error_messages,
            }
            if field_props["type"] == "string":
                kwargs["max_length"] = min(
                    MAX_SETTINGS_VALUE_LENGTH, field_props.get("maxLength", MAX_SETTINGS_VALUE_LENGTH)
                )
            self.fields[field_name] = field_type(**kwargs)


class PluginSettingAddEditForm(forms.Form):
    """Form for adding a single setting, use setting name to populate schema field propertis into form field."""

    error_messages = {
        "required": _("This field is required."),
    }

    def __init__(self, plugin_schema, setting_name, setting_value=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugin_schema = plugin_schema
        self.setting_name = setting_name
        self.setting_value = setting_value
        self.populate_field()

    def populate_field(self):
        field = self.plugin_schema["properties"][self.setting_name]
        help_text = ""
        initial = ""
        if "description" in field:
            help_text = field["description"]
        if self.setting_value:
            initial = self.setting_value
        if field:
            field_type = FIELD_TYPES[field["type"]]
            kwargs = {
                "required": self.setting_name in self.plugin_schema["required"],
                "label": field.get("title", field),
                "help_text": _(help_text),
                "error_messages": self.error_messages,
                "initial": initial,
            }
            if field["type"] == "string":
                kwargs["max_length"] = min(MAX_SETTINGS_VALUE_LENGTH, field.get("maxLength", MAX_SETTINGS_VALUE_LENGTH))

            self.fields[self.setting_name] = field_type(**kwargs)
