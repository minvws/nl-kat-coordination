from typing import Dict

from django import forms

from tools.forms.base import BaseRockyForm


class JsonSchemaForm(BaseRockyForm):
    def __init__(self, schema: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.schema = schema

        fields = self.generate_form_fields(schema)
        for name, field in fields.items():
            self.fields[name] = field

    def generate_form_fields(self, schema: dict) -> Dict[str, forms.fields.Field]:
        fields = {}

        for name, field in schema["properties"].items():
            if field["type"] == "object":  # This is a sub-schema
                fields[name] = JsonSchemaForm(field)  # TODO: render properly, perhaps define max depth?

            required = name in schema["required"]

            if field["type"] == "array":
                fields[name] = forms.CharField(max_length=256, label=name, required=required)  # TODO: comma separated?

            elif field["type"] == "string":
                fields[name] = forms.CharField(max_length=256, label=name, required=required)

            elif field["type"] == "integer":  # TODO: other types
                fields[name] = forms.IntegerField(label=name, required=required)

        return fields
