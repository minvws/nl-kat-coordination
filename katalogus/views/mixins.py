from typing import Any

import structlog
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse

from account.mixins import OrganizationView
from katalogus.client import KATalogus
from katalogus.models import Boefje, Normalizer

logger = structlog.get_logger(__name__)


class SinglePluginView(OrganizationView):
    katalogus_client: KATalogus
    plugin: Boefje | Normalizer

    def setup(self, request: HttpRequest, *args: Any, plugin_id: int, **kwargs: Any) -> None:
        """
        Prepare organization info and KAT-alogus API client.
        """
        super().setup(request, *args, plugin_id=plugin_id, **kwargs)
        self.katalogus_client = self.get_katalogus()
        self.plugin = self.get_plugin(plugin_id, **kwargs)
        self.plugin_schema = self.plugin.schema if isinstance(self.plugin, Boefje) else None

    def get_plugin(self, plugin_id: int, **kwargs) -> Boefje | Normalizer:
        return self.katalogus_client.get_plugin(plugin_id, kwargs["plugin_type"])

    def dispatch(self, request, *args, **kwargs):
        if not self.plugin:
            return redirect(reverse("katalogus", kwargs={"organization_code": self.organization.code}))

        return super().dispatch(request, *args, **kwargs)

    def is_required_field(self, field: str) -> bool:
        """Check whether this field should be required, defaults to False."""
        return bool(self.plugin_schema and field in self.plugin_schema.get("required", []))

    def is_secret_field(self, field: str) -> bool:
        """Check whether this field should be secret, defaults to False."""
        return bool(self.plugin_schema and field in self.plugin_schema.get("secret", []))


class SingleBoefjeView(SinglePluginView):
    def get_plugin(self, plugin_id: int, **kwargs) -> Boefje | Normalizer:
        return self.katalogus_client.get_plugin(plugin_id, "boefje")


class SingleNormalizerView(SinglePluginView):
    def get_plugin(self, plugin_id: int, **kwargs) -> Boefje | Normalizer:
        return self.katalogus_client.get_plugin(plugin_id, "normalizer")
