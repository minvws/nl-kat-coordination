from django.core.management.base import BaseCommand

from katalogus.worker.repository import get_local_repository
from plugins.models import Plugin


class Command(BaseCommand):
    help = "New sync all local plugins."

    def handle(self, *args, **options):
        nsync()


def nsync() -> list[Plugin]:
    plugins = []

    for boefje_id, resource in get_local_repository().resolve_boefjes().items():
        plugins.append(
            Plugin(
                plugin_id=boefje_id,
                name=resource.boefje.name,
                description=resource.boefje.description,
                scan_level=resource.boefje.scan_level,
                consumes=list(resource.boefje.consumes),
                recurrences=resource.boefje.recurrences,
                oci_image=resource.boefje.oci_image,
                oci_arguments=list(resource.boefje.oci_arguments),
                version=resource.boefje.version,
            )
        )

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
