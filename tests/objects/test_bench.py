import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import connections
from django.db.models import Case, Count, F, When
from djangoql.queryset import apply_search
from djangoql.schema import DjangoQLSchema, IntField

from objects.management.commands.generate_benchmark_data import generate
from objects.models import Hostname, IPAddress, IPPort, ScanLevel, bulk_insert
from objects.views import HostnameDetailView, HostnameListView, IPAddressDetailView, IPAddressListView
from plugins.models import Plugin
from tasks.models import ObjectSet, Schedule, Task
from tasks.tasks import recalculate_scan_levels, run_schedule
from tests.conftest import setup_request


@pytest.fixture
def bulk_data(organization, xtdb):
    """Generate bulk data without DNS records for basic testing."""
    hostnames, ips, ports, a_records, aaaa_records, ns_records, mx_records, txt_records, caa_records, scan_levels = (
        generate(organization, 10_000, 2, 1, 2, include_dns_records=False)
    )
    bulk_insert(hostnames)
    bulk_insert(ips)
    bulk_insert(ports)
    bulk_insert(scan_levels)
    bulk_insert(a_records)


@pytest.fixture
def bulk_data_with_dns(organization, xtdb):
    """Generate bulk data WITH DNS records for business rule testing."""
    hostnames, ips, ports, a_records, aaaa_records, ns_records, mx_records, txt_records, caa_records, scan_levels = (
        generate(organization, 10_000, 2, 1, 2, include_dns_records=True)
    )
    bulk_insert(hostnames)
    bulk_insert(ips)
    bulk_insert(ports)
    bulk_insert(a_records)
    if aaaa_records:
        bulk_insert(aaaa_records)
    if ns_records:
        bulk_insert(ns_records)
    if mx_records:
        bulk_insert(mx_records)
    if txt_records:
        bulk_insert(txt_records)
    if caa_records:
        bulk_insert(caa_records)
    bulk_insert(scan_levels)


# ============================================================================
# QUERY BENCHMARKS
# ============================================================================


def test_query_many_hostnames(bulk_data, benchmark):
    """Benchmark querying hostnames with filtering."""

    def select():
        list(Hostname.objects.select_related("network").filter(name__contains="123"))

    benchmark(select)


def test_query_many_ipaddresses(bulk_data, benchmark):
    """Benchmark querying IP addresses with filtering."""

    def select():
        list(IPAddress.objects.select_related("network").filter(address__contains="192"))

    benchmark(select)


def test_query_list_view_fast(bulk_data, benchmark):
    """Benchmark the fast JOIN approach for list views."""

    def raw():
        with connections["xtdb"].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT  V1.*, MAX(V0."scan_level") as max_scan_level
                FROM {Hostname._meta.db_table} V1
                JOIN {ScanLevel._meta.db_table} V0 ON V0."object_id" = V1."_id"
                LIMIT 20
            """,  # noqa: S608
                {},
            )

    benchmark(raw)


# ============================================================================
# LIST VIEW BENCHMARKS
# ============================================================================


def test_hostname_list_view(bulk_data, rf, superuser_member, benchmark):
    """Benchmark hostname list view rendering with scan level annotations."""

    def render_list_view():
        request = setup_request(rf.get("/objects/hostname/"), superuser_member.user)
        view = HostnameListView.as_view()
        response = view(request)
        response.render()
        return response

    result = benchmark(render_list_view)
    assert result.status_code == 200


def test_ipaddress_list_view(bulk_data, rf, superuser_member, benchmark):
    """Benchmark IP address list view rendering with scan level annotations."""

    def render_list_view():
        request = setup_request(rf.get("/objects/ipaddress/"), superuser_member.user)
        view = IPAddressListView.as_view()
        response = view(request)
        response.render()
        return response

    result = benchmark(render_list_view)
    assert result.status_code == 200


def test_hostname_list_view_filtered(bulk_data, rf, superuser_member, benchmark):
    """Benchmark hostname list view with filters applied."""

    def render_filtered_view():
        request = setup_request(rf.get("/objects/hostname/?name=test"), superuser_member.user)
        view = HostnameListView.as_view()
        response = view(request)
        response.render()
        return response

    result = benchmark(render_filtered_view)
    assert result.status_code == 200


def test_ipaddress_list_view_filtered(bulk_data, rf, superuser_member, benchmark):
    """Benchmark IP address list view with filters applied."""

    def render_filtered_view():
        request = setup_request(rf.get("/objects/ipaddress/?&address=10"), superuser_member.user)
        view = IPAddressListView.as_view()
        response = view(request)
        response.render()
        return response

    result = benchmark(render_filtered_view)
    assert result.status_code == 200


# ============================================================================
# DETAIL VIEW BENCHMARKS
# ============================================================================


def test_hostname_detail_view(bulk_data, rf, superuser_member, benchmark):
    """Benchmark hostname detail view with related objects."""
    hostname = Hostname.objects.first()

    def render_detail_view():
        request = setup_request(rf.get(f"/objects/hostname/{hostname.pk}/"), superuser_member.user)
        view = HostnameDetailView.as_view()
        response = view(request, pk=hostname.pk)
        response.render()
        return response

    result = benchmark(render_detail_view)
    assert result.status_code == 200


def test_ipaddress_detail_view(bulk_data, rf, superuser_member, benchmark):
    """Benchmark IP address detail view with related objects."""
    ipaddress = IPAddress.objects.first()

    def render_detail_view():
        request = setup_request(rf.get(f"/objects/ipaddress/{ipaddress.pk}/"), superuser_member.user)
        view = IPAddressDetailView.as_view()
        response = view(request, pk=ipaddress.pk)
        response.render()
        return response

    result = benchmark(render_detail_view)
    assert result.status_code == 200


def test_object_set(bulk_data_with_dns, benchmark):
    object_set = ObjectSet.objects.create(
        name="Test Set",
        object_type=ContentType.objects.get_for_model(Hostname),
        object_query="dnsnsrecord_nameserver != None",
    )

    def inner():
        return object_set.get_query_objects().count()

    result = benchmark.pedantic(inner, rounds=1)
    assert result == 499


# ============================================================================
# SCAN LEVEL RECALCULATION BENCHMARKS
# ============================================================================


def test_scan_level_recalculation(benchmark, bulk_data_with_dns, organization):
    # The ipaddresses van scan level 1 and all hostnames 2
    result = benchmark.pedantic(recalculate_scan_levels, rounds=1)  # Subsequent rounds have no updates
    assert len(result) == 7499


# ============================================================================
# BUSINESS RULE BENCHMARKS
# ============================================================================


class HostnameQLSchema(DjangoQLSchema):
    """Custom schema to support nameservers_with_ipv6_count field"""

    def get_fields(self, model):
        fields = super().get_fields(model)
        if model == Hostname:
            fields += [IntField(name="nameservers_with_ipv6_count")]
        return fields


@pytest.mark.skip
def test_business_rule_ipv6_webservers(bulk_data_with_dns, benchmark):
    """Benchmark: Check hostnames without IPv6 (webservers)."""

    def run_rule():
        query = "dnsnsrecord_nameserver = None and dnsaaaarecord = None"
        return apply_search(Hostname.objects.distinct(), query).count()

    result = benchmark(run_rule)
    assert result >= 0


@pytest.mark.skip
def test_business_rule_ipv6_nameservers(bulk_data_with_dns, benchmark):
    """Benchmark: Check nameservers without IPv6."""

    def run_rule():
        query = "dnsnsrecord_nameserver != None and dnsaaaarecord = None"
        return apply_search(Hostname.objects.distinct(), query).count()

    result = benchmark(run_rule)
    assert result >= 0


@pytest.mark.skip
def test_business_rule_two_ipv6_nameservers(bulk_data_with_dns, benchmark):
    """Benchmark: Check domains with less than 2 IPv6 nameservers."""

    def run_rule():
        queryset = Hostname.objects.annotate(
            nameservers_with_ipv6_count=Count(
                Case(
                    When(dnsnsrecord__name_server__dnsaaaarecord__isnull=False, then=F("dnsnsrecord__name_server_id")),
                    default=None,
                ),
                distinct=True,
            )
        )
        query = "dnsnsrecord_nameserver = None and nameservers_with_ipv6_count < 2"
        return apply_search(queryset, query, HostnameQLSchema).count()

    result = benchmark(run_rule)
    assert result >= 0


@pytest.mark.skip
def test_business_rule_missing_spf(bulk_data_with_dns, benchmark):
    """Benchmark: Check hostnames missing SPF records."""

    def run_rule():
        query = 'dnstxtrecord.value not startswith "v=spf1"'
        return apply_search(Hostname.objects.all(), query).count()

    result = benchmark(run_rule)
    assert result >= 0


@pytest.mark.skip
def test_business_rule_open_sysadmin_port(bulk_data_with_dns, benchmark):
    """Benchmark: Check for open sysadmin ports (SSH, FTP, Telnet, VNC)."""

    def run_rule():
        query = 'protocol = "TCP" and port in (21, 22, 23, 5900)'
        return apply_search(IPPort.objects.all(), query).count()

    result = benchmark(run_rule)
    assert result >= 0


@pytest.mark.skip
def test_business_rule_open_database_port(bulk_data_with_dns, benchmark):
    """Benchmark: Check for open database ports."""

    def run_rule():
        query = 'protocol = "TCP" and port in (1433, 1434, 3050, 3306, 5432)'
        return apply_search(IPPort.objects.all(), query).count()

    result = benchmark(run_rule)
    assert result >= 0


@pytest.mark.skip
def test_business_rule_missing_caa(bulk_data_with_dns, benchmark):
    """Benchmark: Check hostnames missing CAA records."""

    def run_rule():
        query = "dnscaarecord = None"
        return apply_search(Hostname.objects.all(), query).count()

    result = benchmark(run_rule)
    assert result >= 0


# ============================================================================
# TASK SCHEDULING BENCHMARKS
# ============================================================================


def test_task_scheduling_scan_level_filter(bulk_data, docker, celery, organization, benchmark):
    plugin = Plugin.objects.create(
        name="test_scan_filter",
        plugin_id="test_scan_filter",
        oci_image="test",
        consumes=["type:hostname"],
        oci_arguments=["bulk"],
        scan_level=2,
        batch_size=500,
    )
    plugin.enable_for(organization)
    schedule = Schedule.objects.filter(plugin=plugin, organization=organization).first()

    def inner():
        return run_schedule(schedule, force=True, celery=celery)

    tasks = benchmark(inner)
    assert len(tasks) == 20


def test_task_status_check_many_tasks(organization, docker, celery, xtdb, benchmark):
    """Benchmark checking status of many tasks."""
    # Create many tasks
    plugin = Plugin.objects.create(
        name="test_bench",
        plugin_id="test_bench",
        oci_image="test",
        oci_arguments=["{hostname}"],
        scan_level=2,
        batch_size=500,
    )
    plugin.enable_for(organization)
    schedule = Schedule.objects.filter(plugin=plugin, organization=organization).first()

    tasks = []
    for i in range(1000):
        task = Task(
            organization=organization,
            type="plugin",
            status="queued",
            data={"plugin_id": plugin.plugin_id, "input_data": [f"test_{i}.com"]},
        )
        tasks.append(task)

    Task.objects.bulk_create(tasks)

    def inner():
        return run_schedule(schedule, force=True, celery=celery)

    result = benchmark(inner)
    assert len(result) == 0


def test_task_scheduling_with_object_set_query(bulk_data, docker, celery, organization, benchmark):
    """Benchmark task scheduling with complex object set queries."""
    plugin = Plugin.objects.create(
        name="query_test",
        plugin_id="query_test",
        oci_image="test",
        consumes=["type:hostname"],
        oci_arguments=["bulk"],
        scan_level=2,
        batch_size=500,
    )
    plugin.enable_for(organization)

    schedule = Schedule.objects.filter(plugin=plugin, organization=organization).first()
    schedule.object_set.object_query = 'name ~ "123"'
    schedule.object_set.save()

    def schedule_with_query():
        return run_schedule(schedule, force=True, celery=celery)

    result = benchmark(schedule_with_query)
    assert len(result) == 20
