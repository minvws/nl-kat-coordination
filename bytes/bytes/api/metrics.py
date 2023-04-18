import shutil

from prometheus_client import CollectorRegistry, Gauge

from bytes.config import get_settings
from bytes.repositories.meta_repository import MetaDataRepository
from bytes.repositories.raw_repository import RawRepository

collector_registry = CollectorRegistry()


bytes_data_organizations_total = Gauge(
    name="bytes_data_organizations_total",
    documentation="Total amount of organizations in the bytes data directory.",
    registry=collector_registry,
)
bytes_data_raw_files_total = Gauge(
    name="bytes_data_raw_files_total",
    documentation="Total amount of raw files in the bytes data directory.",
    registry=collector_registry,
    labelnames=["organization_id"],
)
bytes_database_organizations_total = Gauge(
    name="bytes_database_organizations_total",
    documentation="Total amount of organizations in the bytes database.",
    registry=collector_registry,
)
bytes_database_raw_files_total = Gauge(
    name="bytes_database_raw_files_total",
    documentation="Total amount of raw files in the bytes database.",
    registry=collector_registry,
    labelnames=["organization_id"],
)
bytes_filesystem_avail_bytes = Gauge(
    name="bytes_filesystem_avail_bytes",
    documentation="Total amount of available bytes of the file system at the mount point.",
    registry=collector_registry,
    labelnames=["mountpoint"],
)
bytes_filesystem_size_bytes = Gauge(
    name="bytes_filesystem_size_bytes",
    documentation="Total amount of bytes of the file system at the mount point.",
    registry=collector_registry,
    labelnames=["mountpoint"],
)


def get_registry(meta_repository: MetaDataRepository, raw_repository: RawRepository) -> CollectorRegistry:
    settings = get_settings()
    organizations = raw_repository.get_organizations()
    bytes_data_organizations_total.set(len(organizations))

    for organization in organizations:
        bytes_data_raw_files_total.labels(organization).set(raw_repository.get_raw_file_count(organization))

    counts_per_organization = meta_repository.get_raw_file_count_per_organization().items()
    bytes_database_organizations_total.set(len(counts_per_organization))

    for organization_id, count in counts_per_organization:
        bytes_database_raw_files_total.labels(organization_id).set(count)

    for mountpoint in settings.bytes_metrics_mountpoints:
        total, used, free = shutil.disk_usage(mountpoint)

        bytes_filesystem_avail_bytes.labels(mountpoint).set(free)
        bytes_filesystem_size_bytes.labels(mountpoint).set(total)

    return collector_registry
