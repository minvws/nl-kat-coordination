from django.core.management.base import BaseCommand

from katalogus.models import Boefje, Normalizer, RunOnDB
from katalogus.worker.repository import get_local_repository


class Command(BaseCommand):
    help = "Sync all local boefjes with the database."

    def handle(self, *args, **options):
        sync()


def sync() -> tuple[list[Boefje], list[Normalizer]]:
    boefjes = []

    for boefje_id, resource in get_local_repository().resolve_boefjes().items():
        boefjes.append(
            Boefje(
                plugin_id=boefje_id,
                static=True,
                name=resource.boefje.name,
                description=resource.boefje.description,
                scan_level=resource.boefje.scan_level,
                consumes=list(resource.boefje.consumes),
                produces=list(resource.boefje.produces),
                schema=resource.boefje.boefje_schema,
                cron=resource.boefje.cron,
                interval=resource.boefje.interval,
                run_on=RunOnDB.from_run_ons(resource.boefje.run_on),
                oci_image=resource.boefje.oci_image,
                oci_arguments=list(resource.boefje.oci_arguments),
                version=resource.boefje.version,
            )
        )

    created_boefjes = Boefje.objects.bulk_create(
        boefjes,
        update_conflicts=True,
        unique_fields=["plugin_id"],
        update_fields=[
            "static",
            "name",
            "description",
            "scan_level",
            "consumes",
            "produces",
            "schema",
            "cron",
            "interval",
            "run_on",
            "oci_image",
            "oci_arguments",
            "version",
        ],
    )
    normalizers = []

    for normalizer_id, resource in get_local_repository().resolve_normalizers().items():
        normalizers.append(
            Normalizer(
                plugin_id=normalizer_id,
                static=True,
                name=resource.normalizer.name,
                description=resource.normalizer.description,
                consumes=list(resource.normalizer.consumes),
                produces=list(resource.normalizer.produces),
                version=resource.normalizer.version,
            )
        )

    created_normalizers = Normalizer.objects.bulk_create(
        normalizers,
        update_conflicts=True,
        unique_fields=["plugin_id"],
        update_fields=["static", "name", "description", "consumes", "produces", "version"],
    )

    return created_boefjes, created_normalizers
