import logging

from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from requests import RequestException

from katalogus.views.mixins import SinglePluginView

logger = logging.getLogger(__name__)


class PluginSettingsListView(SinglePluginView, ListView):
    """
    Shows all settings available for a specific plugin (plugin schema settings).
    """

    def get(self, request, *args, **kwargs):
        try:
            self.object_list = self.get_queryset()
        except RequestException:
            messages.add_message(
                self.request, messages.ERROR, _("Failed getting settings for boefje {}").format(self.plugin.id)
            )
            self.object_list = []

        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        """Gets schema setting with additional info of the value of a setting."""
        if self.plugin_schema is None:
            return []

        settings = self.katalogus_client.get_plugin_settings(plugin_id=self.plugin.id)
        props = self.plugin_schema["properties"]

        return [
            {
                "name": prop,
                "value": settings.get(prop),
                "required": self.is_required_field(prop),
                "secret": self.is_secret_field(prop),
            }
            for prop in props
        ]
