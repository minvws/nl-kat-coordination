import os
import shutil

import prometheus_client

from bytes.config import get_settings

collector_registry = prometheus_client.CollectorRegistry()

# note: this could also be inferred from the one below, so should we add it?
bytes_data_organizations_total = prometheus_client.Gauge(
    name="bytes_data_organizations_total",
    documentation="Total amount of organizations in the bytes data directory.",
    registry=collector_registry,
)
bytes_data_raw_files_total = prometheus_client.Gauge(
    name="bytes_data_raw_files_total",
    documentation="Total amount of raw files in the bytes data directory.",
    registry=collector_registry,
    labelnames=["organization_id"],
)
bytes_filesystem_avail_bytes = prometheus_client.Gauge(
    name="bytes_filesystem_avail_bytes",
    documentation="Total amount of available bytes of the file system.",
    registry=collector_registry,
    labelnames=["mountpoint"],
)
bytes_filesystem_size_bytes = prometheus_client.Gauge(
    name="bytes_filesystem_size_bytes",
    documentation="Total amount of bytes of the file system.",
    registry=collector_registry,
    labelnames=["mountpoint"],
)


def get_registry():
    settings = get_settings()
    organization_paths = list(settings.bytes_data_dir.iterdir())
    bytes_data_organizations_total.set(len(organization_paths))

    for organization_path in organization_paths:
        number_of_files = sum([len(a[-1]) for a in list(os.walk(organization_path))])
        bytes_data_raw_files_total.labels(organization_path.name).set(number_of_files)

    mountpoint = "/"
    total, used, free = shutil.disk_usage(mountpoint)

    bytes_filesystem_avail_bytes.labels(mountpoint).set(free)
    bytes_filesystem_size_bytes.labels(mountpoint).set(total)

    return collector_registry
