from django.views.generic import ListView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator


@class_view_decorator(otp_required)
class PluginSettingsListView(ListView):
    """
    Shows all settings available for a specific plugin (plugin schema settings).
    """

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        """Gets schema setting with additional info of the value of a setting."""
        queryset = []
        if self.plugin_schema:
            for schema_props in self.plugin_schema["properties"]:
                setting = self.katalogus_client.get_plugin_setting(plugin_id=self.plugin["id"], name=schema_props)
                if "message" in setting:
                    value = ""
                else:
                    value = setting
                queryset.append(
                    {"name": schema_props, "value": value, "required": schema_props in self.plugin_schema["required"]}
                )
        return queryset
