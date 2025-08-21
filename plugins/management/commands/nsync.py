from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from pydantic import BaseModel, Field, TypeAdapter

from katalogus.worker.repository import get_local_repository
from plugins.models import Plugin


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

    for normalizer_id, resource in get_local_repository().resolve_normalizers().items():
        plugins.append(
            Plugin(
                plugin_id=normalizer_id,
                name=resource.normalizer.name,
                scan_level=resource.normalizer.scan_level,
                description=resource.normalizer.description,
                consumes=list(resource.normalizer.consumes),
                recurrences=resource.normalizer.recurrences,
                version=resource.normalizer.version,
            )
        )

    plugins_path = Path(settings.BASE_DIR / "plugins" / "plugins" / "plugins.json")
    for plugin in plugins_type_adapter.validate_json(plugins_path.read_text()):
        plugins.append(
            Plugin(
                plugin_id=plugin.plugin_id,
                name=plugin.name,
                scan_level=plugin.scan_level,
                description=plugin.description,
                consumes=list(plugin.consumes),
                recurrences=plugin.recurrences,
                oci_image=plugin.oci_image,
                oci_arguments=plugin.oci_arguments,
                version=plugin.version,
            )
        )

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

    return created_plugins
