import functools
import os
import shutil
import time
from typing import Optional

import prometheus_client

from bytes.config import get_settings

collector_registry = prometheus_client.CollectorRegistry()


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


@functools.lru_cache(maxsize=get_settings().metrics_cache_ttl_seconds)
def get_number_of_raw_files_for_organization(organization_path: str, ttl_hash: Optional[int] = None):  # noqa: F841
    count = 0

    # The os.listdir approach seems to be the fastest python-native way to do this.
    for index_path in os.listdir(organization_path):
        count += len(os.listdir(f"{organization_path}/{index_path}"))

    return count


def get_registry():
    settings = get_settings()
    organization_paths = os.listdir(str(settings.bytes_data_dir.absolute()))
    bytes_data_organizations_total.set(len(organization_paths))

    for organization_path in organization_paths:
        count = get_number_of_raw_files_for_organization(
            str(settings.bytes_data_dir.joinpath(organization_path).absolute()),
            # Second argument changes every `metrics_cache_ttl_seconds` seconds, keeping the result cached for that time
            round(time.time() / settings.metrics_cache_ttl_seconds),
        )
        bytes_data_raw_files_total.labels(organization_path).set(count)

    mountpoint = "/"
    total, used, free = shutil.disk_usage(mountpoint)

    bytes_filesystem_avail_bytes.labels(mountpoint).set(free)
    bytes_filesystem_size_bytes.labels(mountpoint).set(total)

    return collector_registry
