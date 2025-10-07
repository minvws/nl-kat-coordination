import pytest
from django.db import connections

from objects.management.commands.generate_benchmark_data import generate
from objects.models import Hostname, ScanLevel, bulk_insert


@pytest.fixture
def bulk_data(organization, xtdb):
    hostnames, ips, ports, scan_levels = generate(organization, 50_000, 2, 2, 2)
    bulk_insert(hostnames)
    bulk_insert(ips)
    bulk_insert(ports)
    bulk_insert(scan_levels)


@pytest.mark.bench
def test_query_many_hostnames(bulk_data, benchmark):
    def select():
        list(Hostname.objects.select_related("network").filter(name__contains="123"))

    benchmark(select)


@pytest.mark.bench
def test_query_list_view(bulk_data, benchmark):
    def raw():
        with connections["xtdb"].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT  *,
                    (SELECT MAX(V0."scan_level")
                    FROM {ScanLevel._meta.db_table} V0
                    WHERE (V0."object_id" = ({Hostname._meta.db_table}."_id") AND V0."object_type" = 'hostname')
                    GROUP BY V0."object_id") as max_scan_level
                FROM {Hostname._meta.db_table}
                LIMIT 20
            """,  # noqa: S608
                {},
            )

    benchmark(raw)
