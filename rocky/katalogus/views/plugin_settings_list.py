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
        if not self.plugin_schema:
            return []

        settings = self.katalogus_client.get_plugin_settings(plugin_id=self.plugin.id)

        return [
            {
                "name": schema_props,
                "value": settings.get(schema_props, ""),
                "required": schema_props in self.plugin_schema["required"],
            }
            for schema_props in self.plugin_schema["properties"]
        ]
