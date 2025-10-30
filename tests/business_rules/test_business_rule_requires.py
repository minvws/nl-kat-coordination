from django.contrib.contenttypes.models import ContentType
from pytest_django.asserts import assertContains

from objects.models import Finding, Hostname, IPAddress, Network
from plugins.models import BusinessRule, Plugin
from plugins.plugins.business_rules import run_rules
from plugins.views import BusinessRuleCreateView, BusinessRuleDetailView, BusinessRuleUpdateView
from tasks.models import Task
from tests.conftest import setup_request


def test_business_rule_create_view_with_requires(rf, superuser_member, xtdb):
    hostname_ct = ContentType.objects.get_for_model(Hostname)
    dns_plugin = Plugin.objects.create(plugin_id="dns", name="DNS Plugin")
    nmap_plugin = Plugin.objects.create(plugin_id="nmap", name="Nmap Plugin")

    request = setup_request(
        rf.post(
            "add_business_rule",
            {
                "name": "New Rule with Requires",
                "object_type": hostname_ct.id,
                "query": 'name = "example.com"',
                "finding_type_code": "KAT-NEW-RULE",
                "requires": [dns_plugin.id, nmap_plugin.id],
            },
        ),
        superuser_member.user,
    )
    response = BusinessRuleCreateView.as_view()(request)

    assert response.status_code == 302
    assert BusinessRule.objects.filter(name="New Rule with Requires").exists()

    rule = BusinessRule.objects.get(name="New Rule with Requires")
    assert rule.requires.count() == 2
    assert dns_plugin in rule.requires.all()
    assert nmap_plugin in rule.requires.all()


def test_business_rule_update_view_add_requires(rf, superuser_member, xtdb):
    hostname_ct = ContentType.objects.get_for_model(Hostname)
    dns_plugin = Plugin.objects.create(plugin_id="dns", name="DNS Plugin")
    nmap_plugin = Plugin.objects.create(plugin_id="nmap", name="Nmap Plugin")
    rule = BusinessRule.objects.create(
        name="Test Rule", object_type=hostname_ct, query='name = "test.com"', finding_type_code="KAT-TEST"
    )

    request = setup_request(
        rf.post(
            "edit_business_rule",
            {
                "name": "Test Rule",
                "enabled": True,
                "object_type": hostname_ct.id,
                "query": 'name = "test.com"',
                "finding_type_code": "KAT-TEST",
                "requires": [dns_plugin.id, nmap_plugin.id],
            },
        ),
        superuser_member.user,
    )
    response = BusinessRuleUpdateView.as_view()(request, pk=rule.pk)
    assert response.status_code == 302

    rule.refresh_from_db()
    assert rule.requires.count() == 2
    assert dns_plugin in rule.requires.all()
    assert nmap_plugin in rule.requires.all()


def test_business_rule_update_view_remove_requires(rf, superuser_member, xtdb):
    hostname_ct = ContentType.objects.get_for_model(Hostname)
    dns_plugin = Plugin.objects.create(plugin_id="dns", name="DNS Plugin")
    nmap_plugin = Plugin.objects.create(plugin_id="nmap", name="Nmap Plugin")
    rule = BusinessRule.objects.create(
        name="Test Rule", object_type=hostname_ct, query='name = "test.com"', finding_type_code="KAT-TEST"
    )
    rule.requires.add(dns_plugin, nmap_plugin)

    request = setup_request(
        rf.post(
            "edit_business_rule",
            {
                "name": "Test Rule",
                "enabled": "on",
                "object_type": hostname_ct.id,
                "query": 'name = "test.com"',
                "finding_type_code": "KAT-TEST",
                "requires": [],
            },
        ),
        superuser_member.user,
    )
    response = BusinessRuleUpdateView.as_view()(request, pk=rule.pk)
    assert response.status_code == 302

    rule.refresh_from_db()
    assert rule.requires.count() == 0


def test_business_rule_detail_view_shows_requires(rf, superuser_member, xtdb):
    hostname_ct = ContentType.objects.get_for_model(Hostname)
    dns_plugin = Plugin.objects.create(plugin_id="dns", name="DNS Plugin")
    nmap_plugin = Plugin.objects.create(plugin_id="nmap", name="Nmap Plugin")

    rule = BusinessRule.objects.create(
        name="Test Rule", object_type=hostname_ct, query='name = "test.com"', finding_type_code="KAT-TEST"
    )
    rule.requires.add(dns_plugin, nmap_plugin)

    request = setup_request(rf.get("business_rule_detail", kwargs={"pk": rule.pk}), superuser_member.user)
    response = BusinessRuleDetailView.as_view()(request, pk=rule.pk)
    assert response.status_code == 200
    assertContains(response, "DNS Plugin")
    assertContains(response, "Nmap Plugin")


def test_business_rule_requires_filters_objects_no_tasks(xtdb):
    network = Network.objects.create(name="test")
    hostname_ct = ContentType.objects.get_for_model(Hostname)
    hn1 = Hostname.objects.create(network=network, name="test1.com")
    hn2 = Hostname.objects.create(network=network, name="test2.com")
    hn3 = Hostname.objects.create(network=network, name="test3.com")
    dns_plugin = Plugin.objects.create(plugin_id="dns", name="DNS Plugin")

    rule = BusinessRule.objects.create(
        name="Test Rule with Requires",
        object_type=hostname_ct,
        query='name in ("test1.com", "test2.com")',
        finding_type_code="KAT-TEST-REQUIRES",
    )
    rule.requires.add(dns_plugin)

    run_rules([rule])
    findings = Finding.objects.filter(finding_type__code="KAT-TEST-REQUIRES")
    assert findings.count() == 0

    Task.objects.create(type="plugin", data={"plugin_id": "dns", "input_data": [str(hn1)]})
    Task.objects.create(type="plugin", data={"plugin_id": "dns", "input_data": [str(hn2)]})

    run_rules([rule])
    findings = Finding.objects.filter(finding_type__code="KAT-TEST-REQUIRES")
    assert findings.count() == 2

    finding_object_ids = {f.hostname_id for f in findings}
    assert hn1.pk in finding_object_ids
    assert hn2.pk in finding_object_ids
    assert hn3.pk not in finding_object_ids


def test_business_rule_requires_multiple_plugins(xtdb):
    network = Network.objects.create(name="test")
    hostname_ct = ContentType.objects.get_for_model(Hostname)
    hn1 = Hostname.objects.create(network=network, name="test1.com")
    hn2 = Hostname.objects.create(network=network, name="test2.com")
    hn3 = Hostname.objects.create(network=network, name="test3.com")
    dns_plugin = Plugin.objects.create(plugin_id="dns", name="DNS Plugin")
    ssl_plugin = Plugin.objects.create(plugin_id="ssl", name="SSL Plugin")

    Task.objects.create(type="plugin", data={"plugin_id": "dns", "input_data": [str(hn1)]})
    Task.objects.create(type="plugin", data={"plugin_id": "ssl", "input_data": [str(hn1)]})
    Task.objects.create(type="plugin", data={"plugin_id": "dns", "input_data": [str(hn2)]})
    Task.objects.create(type="plugin", data={"plugin_id": "ssl", "input_data": [str(hn3)]})

    rule = BusinessRule.objects.create(
        name="Test Rule with Multiple Requires",
        object_type=hostname_ct,
        query='name in ("test1.com", "test2.com", "test3.com")',
        finding_type_code="KAT-TEST-MULTI-REQUIRES",
    )
    rule.requires.add(dns_plugin, ssl_plugin)

    run_rules([rule])
    findings = Finding.objects.filter(finding_type__code="KAT-TEST-MULTI-REQUIRES")
    assert findings.count() == 1
    assert findings.first().hostname_id == hn1.pk


def test_business_rule_no_requires_creates_all_findings(xtdb):
    network = Network.objects.create(name="test")
    hostname_ct = ContentType.objects.get_for_model(Hostname)
    hn1 = Hostname.objects.create(network=network, name="test1.com")
    hn2 = Hostname.objects.create(network=network, name="test2.com")
    rule = BusinessRule.objects.create(
        name="None", object_type=hostname_ct, query='name in ("test1.com", "test2.com")', finding_type_code="KAT-NO"
    )

    run_rules([rule])
    findings = Finding.objects.filter(finding_type__code="KAT-NO")
    assert findings.count() == 2
    assert {f.hostname_id for f in findings} == {hn1.pk, hn2.pk}


def test_business_rule_requires_with_ip_addresses(xtdb):
    network = Network.objects.create(name="test")
    ip_ct = ContentType.objects.get_for_model(IPAddress)
    ip1 = IPAddress.objects.create(network=network, address="192.168.1.1")
    IPAddress.objects.create(network=network, address="192.168.1.2")
    nmap_plugin = Plugin.objects.create(plugin_id="nmap", name="Nmap Plugin")

    Task.objects.create(type="plugin", data={"plugin_id": "nmap", "input_data": [str(ip1)]})
    rule = BusinessRule.objects.create(
        name="IP", object_type=ip_ct, query='address in ("192.168.1.1", "192.168.1.2")', finding_type_code="KAT-TEST-IP"
    )
    rule.requires.add(nmap_plugin)

    run_rules([rule])
    findings = Finding.objects.filter(finding_type__code="KAT-TEST-IP")
    assert findings.count() == 1
    assert findings.first().address_id == ip1.pk
