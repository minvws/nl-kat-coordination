import datetime

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from pytest_django.asserts import assertContains, assertNotContains

from objects.models import Hostname, IPAddress, IPPort
from plugins.models import EnabledPlugin, Plugin
from plugins.views import EnabledPluginUpdateView, EnabledPluginView, PluginDeleteView, PluginListView
from tasks.models import Schedule
from tests.conftest import setup_request


def test_plugin_list(rf, superuser_member):
    plugin = Plugin.objects.create(name="testing plugins", plugin_id="testt")
    request = setup_request(rf.get("plugin_list"), superuser_member.user)
    response = PluginListView.as_view()(request)

    assert response.status_code == 200
    assertContains(response, "testing plugins")
    assertContains(response, "Enable")
    assertNotContains(response, " Disable")
    assertContains(response, '<form action=" /en/enabled-plugin/ ')

    enabled_plugin = plugin.enable_for(None)

    response = PluginListView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, "testing plugins")
    assertNotContains(response, " Enable")
    assertContains(response, " Disable")
    assertContains(response, f'<form action=" /en/enabled-plugin/{enabled_plugin.id}')

    enabled_plugin.enabled = False
    enabled_plugin.save()

    response = PluginListView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, f'<form action=" /en/enabled-plugin/{enabled_plugin.id}')

    Plugin.objects.create(name="testing plugins 2", plugin_id="testt 2")
    response = PluginListView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, '<form action=" /en/enabled-plugin/ ')
    assertContains(response, f'<form action=" /en/enabled-plugin/{enabled_plugin.id}')


def test_plugin_query_with_enabled(organization, organization_b):
    plugin_1 = Plugin.objects.create(name="1", plugin_id="1")
    plugin_1.enable_for(organization)
    Plugin.objects.create(name="2", plugin_id="2").enable_for(organization_b)
    plugin_3 = Plugin.objects.create(name="3", plugin_id="3")
    plugin_3.enable_for(None)
    plugin_3.enable_for(organization)
    Plugin.objects.create(name="4", plugin_id="4")

    assert {plugin.plugin_id: plugin.enabled for plugin in Plugin.objects.with_enabled(None)} == {
        "1": False,
        "2": False,
        "3": True,
        "4": False,
    }

    assert {plugin.plugin_id: plugin.enabled for plugin in Plugin.objects.with_enabled(organization)} == {
        "1": True,
        "2": False,
        "3": True,
        "4": False,
    }

    assert {plugin.plugin_id: plugin.enabled for plugin in Plugin.objects.with_enabled(organization_b)} == {
        "1": False,
        "2": True,
        "3": True,
        "4": False,
    }

    plugin_3.disable_for(organization_b)

    assert {plugin.plugin_id: plugin.enabled for plugin in Plugin.objects.with_enabled(organization_b)} == {
        "1": False,
        "2": True,
        "3": False,
        "4": False,
    }

    plugin_1.disable_for(organization)
    assert {plugin.plugin_id: plugin.enabled for plugin in Plugin.objects.with_enabled(organization_b)} == {
        "1": False,
        "2": True,
        "3": False,
        "4": False,
    }


def test_enable_plugins(rf, superuser_member):
    plugin = Plugin.objects.create(name="test", plugin_id="testt")
    request = setup_request(
        rf.post("plugin_enabled", {"organization": "", "enabled": True, "plugin": plugin.id}), superuser_member.user
    )
    response = EnabledPluginView.as_view()(request)

    assert response.status_code == 302
    assert response.headers["Location"] == "/en/plugins/"
    enabled_plugin = EnabledPlugin.objects.first()

    assert enabled_plugin
    assert enabled_plugin.enabled is True

    request = setup_request(
        rf.post("plugin_enabled", {"organization": "", "enabled": False, "plugin": plugin.id}), superuser_member.user
    )
    response = EnabledPluginUpdateView.as_view()(request, pk=enabled_plugin.id)
    assert response.status_code == 302
    assert response.headers["Location"] == "/en/plugins/"

    assert EnabledPlugin.objects.count() == 1
    enabled_plugin.refresh_from_db()
    assert enabled_plugin.enabled is False

    request = setup_request(rf.post("plugin_enabled", {"enabled": False, "plugin": plugin.id}), superuser_member.user)
    response = EnabledPluginUpdateView.as_view()(request, pk=enabled_plugin.id)
    assert response.status_code == 302
    assert response.headers["Location"] == "/en/plugins/"


def test_delete_plugin(rf, superuser_member, client_member):
    plugin = Plugin.objects.create(name="1", plugin_id="1")
    request = setup_request(rf.post("delete_plugin"), superuser_member.user)
    response = PluginDeleteView.as_view()(request, pk=plugin.id)

    assert response.status_code == 302
    assert response.headers["Location"] == "/en/plugins/"
    assert Plugin.objects.count() == 0

    plugin = Plugin.objects.create(name="2", plugin_id="2")
    request = setup_request(rf.post("delete_plugin"), client_member.user)

    with pytest.raises(PermissionDenied):
        PluginDeleteView.as_view()(request, pk=plugin.id)


def test_enabling_plugin_creates_schedule():
    plugin = Plugin.objects.create(name="test", plugin_id="testt")
    enabled_plugin = EnabledPlugin.objects.create(enabled=True, plugin=plugin)

    schedule = Schedule.objects.filter(plugin=enabled_plugin.plugin).first()
    now = datetime.datetime.now(datetime.UTC)

    # minute precision should be stable to test
    assert f"DTSTART:{now.strftime('%Y%m%dT%H%M')}" in str(schedule.recurrences)
    assert "RRULE:FREQ=DAILY" in str(schedule.recurrences)

    assert schedule.enabled
    assert schedule.organization is None
    assert schedule.object_set is None
    assert schedule.run_on is None
    assert schedule.operation is None

    plugin = Plugin.objects.create(name="test2", plugin_id="testt2", consumes=["type:hostname"])
    enabled_plugin = EnabledPlugin.objects.create(enabled=True, plugin=plugin)
    schedule = Schedule.objects.filter(plugin=enabled_plugin.plugin).first()

    assert schedule.enabled
    assert schedule.object_set is not None
    assert schedule.object_set.object_query == ""
    assert schedule.object_set.object_type == ContentType.objects.get(model="hostname")
    assert len(schedule.object_set.traverse_objects()) == 0


def test_enabled_organizations(organization, organization_b):
    plugin = Plugin.objects.create(name="test", plugin_id="testt")
    enabled_plugin = EnabledPlugin.objects.create(enabled=True, plugin=plugin)

    assert plugin.enabled_organizations().count() == 2  # Globally enabled

    enabled_plugin.organization = organization
    enabled_plugin.save()

    assert plugin.enabled_organizations().count() == 1
    assert plugin.enabled_organizations().first() == organization

    enabled_plugin.enabled = False
    enabled_plugin.save()

    assert plugin.enabled_organizations().count() == 0

    EnabledPlugin.objects.create(enabled=True, plugin=plugin)
    assert plugin.enabled_organizations().count() == 1
    assert plugin.enabled_organizations().first() == organization_b  # The organization-specific item takes precedence

    enabled_plugin.enabled = True
    enabled_plugin.save()

    assert plugin.enabled_organizations().count() == 2


def test_enabled_for(organization, organization_b):
    plugin = Plugin.objects.create(name="test", plugin_id="testt")
    enabled_plugin = EnabledPlugin.objects.create(enabled=True, plugin=plugin)

    assert plugin.enabled_organizations().count() == 2  # Globally enabled
    assert plugin.enabled_for(organization) is True
    assert plugin.enabled_for(organization_b) is True

    enabled_plugin.organization = organization
    enabled_plugin.save()

    assert plugin.enabled_organizations().count() == 1
    assert plugin.enabled_organizations().first() == organization
    assert plugin.enabled_for(organization) is True
    assert plugin.enabled_for(organization_b) is False


def test_arguments():
    assert Plugin(name="t", plugin_id="t").types_in_arguments() == []
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{hostname}"]).types_in_arguments() == [Hostname]
    assert Plugin(
        name="t", plugin_id="t", oci_arguments=["run {hostname} A || run {hostname} AAAA || run {hostname} CNAME"]
    ).types_in_arguments() == [Hostname]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["test", "{HOSTNAME}"]).types_in_arguments() == [Hostname]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["test", "{ipaddress}"]).types_in_arguments() == [IPAddress]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["test", "{ipaddress|hostname}"]).types_in_arguments() == []
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{ipport}", "test"]).types_in_arguments() == [IPPort]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{ipport}", "{ipport}"]).types_in_arguments() == [IPPort]
    assert set(Plugin(name="t", plugin_id="t", oci_arguments=["{ipport}", "{ipaddress}"]).types_in_arguments()) == {
        IPPort,
        IPAddress,
    }

    assert Plugin(name="t", plugin_id="t", oci_arguments=["{}"]).types_in_arguments() == []
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{file}"]).types_in_arguments() == []
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{bla}"]).types_in_arguments() == []
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{Protocol}"]).types_in_arguments() == []
    assert Plugin(name="t", plugin_id="t", consumes=["type:hostname"]).types_in_arguments() == []
    assert Plugin(name="t", plugin_id="t", consumes=["type:HOSTNAME"]).types_in_arguments() == []

    assert Plugin(name="t", plugin_id="t").consumed_types() == []
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{hostname}"]).consumed_types() == [Hostname]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["test", "{HOSTNAME}"]).consumed_types() == [Hostname]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["test", "{ipaddress}"]).consumed_types() == [IPAddress]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{ipport}", "test"]).consumed_types() == [IPPort]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{}"]).consumed_types() == []
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{file}"]).consumed_types() == []
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{bla}"]).consumed_types() == []
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{Protocol}"]).consumed_types() == []
    assert Plugin(name="t", plugin_id="t", consumes=["type:hostname"]).consumed_types() == [Hostname]
    assert Plugin(name="t", plugin_id="t", consumes=["type:HOSTNAME"]).consumed_types() == [Hostname]

    assert Plugin(name="t", plugin_id="t", consumes=["file:type"]).files_in_arguments() == ["type"]
    assert Plugin(name="t", plugin_id="t").files_in_arguments() == []
