import json
import pkgutil
from pathlib import Path

import structlog
from django.conf import settings

from plugins.models import Plugin

logger = structlog.get_logger(__name__)


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
    raw_plugins = []
    plugins = []

    raw_plugins.extend(json.loads(Path(settings.BASE_DIR / "plugins" / "plugins" / "plugins.json").read_text()))
    raw_plugins.extend(json.loads(Path(settings.BASE_DIR / "plugins" / "plugins" / "nuclei_plugins.json").read_text()))

    for raw_plugin in raw_plugins:
        plugin = Plugin(
            plugin_id=raw_plugin.get("plugin_id"),
            name=raw_plugin.get("name"),
            scan_level=raw_plugin.get("scan_level", 1),
            description=raw_plugin.get("description"),
            consumes=raw_plugin.get("consumes", []),
            recurrences=raw_plugin.get("recurrences"),
            batch_size=raw_plugin.get("batch_size"),
            oci_image=raw_plugin.get("oci_image"),
            oci_arguments=raw_plugin.get("oci_arguments", []),
            version=raw_plugin.get("version"),
            permissions=raw_plugin.get("permissions", {}),
        )
        plugins.append(plugin)

    return Plugin.objects.bulk_create(
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
            "permissions",
        ],
    )
