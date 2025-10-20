import json
import pkgutil
from pathlib import Path

import structlog
from django.conf import settings
from pydantic import BaseModel, Field, TypeAdapter

from plugins.models import Plugin

logger = structlog.get_logger(__name__)


class NewPlugin(BaseModel):
    plugin_id: str
    name: str
    description: str | None = None
    scan_level: int = 1
    consumes: set[str] = Field(default_factory=set)
    recurrences: str | None = None
    batch_size: int | None = None
    oci_image: str | None = None
    oci_arguments: list[str] = Field(default_factory=list)
    version: str | None = None

    def __str__(self):
        return f"{self.plugin_id}:{self.version}"


plugins_type_adapter = TypeAdapter(list[NewPlugin])


def _find_packages_in_path_containing_files(path: Path, required_files: tuple[str, ...]) -> list[tuple[Path, str]]:
    prefix = create_relative_import_statement_from_cwd(path)
    paths = []

    for package in pkgutil.walk_packages([str(path)], prefix):
        if not package.ispkg:
            logger.debug("%s is not a package", package.name)
            continue

        new_path = path / package.name.replace(prefix, "").replace(".", "/")
        missing_files = [file for file in required_files if not (new_path / file).exists()]

        if missing_files:
            logger.debug("Files %s not found for %s", missing_files, package.name)
            continue

        paths.append((new_path, package.name))

    return paths


def create_relative_import_statement_from_cwd(package_dir: Path) -> str:
    relative_path = str(package_dir.absolute()).replace(str(Path().cwd()), "")  # e.g. "/abc/def"

    return f"{relative_path[1:].replace('/', '.')}." if relative_path else ""  # Turns into "abc.def."


def sync() -> list[Plugin]:
    plugins = []

    for path, package in _find_packages_in_path_containing_files(
        settings.BASE_DIR / "plugins" / "plugins", ("plugin.json",)
    ):
        definition = json.loads(path.joinpath("plugin.json").read_text())
        plugin = Plugin(
            plugin_id=definition.get("plugin_id"),
            name=definition.get("name"),
            scan_level=definition.get("scan_level", 1),
            description=definition.get("description"),
            consumes=definition.get("consumes", []),
            recurrences=definition.get("recurrences"),
            batch_size=definition.get("batch_size"),
            oci_image=definition.get("oci_image"),
            oci_arguments=definition.get("oci_arguments", []),
            version=definition.get("version"),
        )
        plugins.append(plugin)

    plugins_path = Path(settings.BASE_DIR / "plugins" / "plugins" / "plugins.json")
    for parsed_plugin in plugins_type_adapter.validate_json(plugins_path.read_text()):
        plugin = Plugin(
            plugin_id=parsed_plugin.plugin_id,
            name=parsed_plugin.name,
            scan_level=parsed_plugin.scan_level,
            description=parsed_plugin.description,
            consumes=list(parsed_plugin.consumes),
            recurrences=parsed_plugin.recurrences,
            batch_size=parsed_plugin.batch_size,
            oci_image=parsed_plugin.oci_image,
            oci_arguments=parsed_plugin.oci_arguments,
            version=parsed_plugin.version,
        )
        plugins.append(plugin)

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
            "batch_size",
            "oci_image",
            "oci_arguments",
            "version",
        ],
    )

    return created_plugins
