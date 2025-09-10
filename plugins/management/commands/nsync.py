import json
from pathlib import Path

import structlog
from django.conf import settings
from django.core.management.base import BaseCommand
from pydantic import BaseModel, Field, TypeAdapter

from katalogus.worker.repository import ModuleException, _find_packages_in_path_containing_files
from openkat.settings import BASE_DIR
from plugins.models import EnabledPlugin, Plugin

logger = structlog.get_logger(__name__)


class Command(BaseCommand):
    help = "New sync all local plugins."

    def handle(self, *args, **options):
        nsync()


class NewPlugin(BaseModel):
    plugin_id: str
    name: str
    description: str | None = None
    scan_level: int = 1
    consumes: set[str] = Field(default_factory=set)
    recurrences: str | None = None
    oci_image: str | None = None
    oci_arguments: list[str] = Field(default_factory=list)
    version: str | None = None

    def __str__(self):
        return f"{self.plugin_id}:{self.version}"


plugins_type_adapter = TypeAdapter(list[NewPlugin])


def nsync() -> list[Plugin]:
    plugins = []
    enabled_plugins = []

    for path, package in _find_packages_in_path_containing_files(BASE_DIR / "plugins" / "plugins", ("plugin.json",)):
        try:
            definition = json.loads(path.joinpath("plugin.json").read_text())
            plugin = Plugin(
                plugin_id=definition.get("plugin_id"),
                name=definition.get("name"),
                scan_level=definition.get("scan_level", 1),
                description=definition.get("description"),
                consumes=definition.get("consumes", []),
                recurrences=definition.get("recurrences"),
                oci_image=definition.get("oci_image"),
                oci_arguments=definition.get("oci_arguments", []),
                version=definition.get("version"),
            )
            plugins.append(plugin)
            enabled_plugins.append(EnabledPlugin(enabled=True, plugin=plugin, organization=None))
        except ModuleException as exc:
            logger.error(exc)

    plugins_path = Path(settings.BASE_DIR / "plugins" / "plugins" / "plugins.json")
    for plugin in plugins_type_adapter.validate_json(plugins_path.read_text()):
        plugin = Plugin(plugin_id=plugin.plugin_id, name=plugin.name, scan_level=plugin.scan_level,
                   description=plugin.description, consumes=list(plugin.consumes), recurrences=plugin.recurrences,
                   oci_image=plugin.oci_image, oci_arguments=plugin.oci_arguments, version=plugin.version, )
        plugins.append(plugin)

        if any("{file}" in arg for arg in plugin.oci_arguments):
            enabled_plugins.append(EnabledPlugin(enabled=True, plugin=plugin, organization=None))

    created_plugins = Plugin.objects.bulk_create(
        plugins,
        update_conflicts=True,
        unique_fields=["plugin_id"],
        update_fields=[
            "description",
            "name",
            "scan_level",
            "consumes",
            "recurrences",
            "oci_image",
            "oci_arguments",
            "version",
        ],
    )
    EnabledPlugin.objects.bulk_create(enabled_plugins, ignore_conflicts=True)

    return created_plugins
