from pytest_django.asserts import assertContains, assertNotContains

from plugins.models import EnabledPlugin, Plugin
from plugins.views import EnabledPluginUpdateView, EnabledPluginView, PluginListView
from tasks.models import NewSchedule
from tests.conftest import setup_request


def test_plugin_list(rf, superuser_member):
    plugin = Plugin.objects.create(name="testing plugins", plugin_id="testt")
    request = setup_request(rf.get("plugin_list"), superuser_member.user)
    response = PluginListView.as_view()(request)

    assert response.status_code == 200
    assertContains(response, "testing plugins")
    assertContains(response, "Enable")
    assertNotContains(response, "Disable")
    assertContains(response, '<form action=" /en/plugins/enabled-plugin ')

    enabled_plugin = EnabledPlugin.objects.create(enabled=True, plugin=plugin, organization=None)

    response = PluginListView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, "testing plugins")
    assertNotContains(response, "Enable")
    assertContains(response, "Disable")
    assertContains(response, f'<form action=" /en/plugins/enabled-plugin/{enabled_plugin.id}')

    enabled_plugin.enabled = False
    enabled_plugin.save()

    response = PluginListView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, f'<form action=" /en/plugins/enabled-plugin/{enabled_plugin.id}')

    Plugin.objects.create(name="testing plugins 2", plugin_id="testt 2")
    response = PluginListView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, '<form action=" /en/plugins/enabled-plugin ')
    assertContains(response, f'<form action=" /en/plugins/enabled-plugin/{enabled_plugin.id}')


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


def test_enabling_plugin_creates_schedule():
    plugin = Plugin.objects.create(name="test", plugin_id="testt")
    enabled_plugin = EnabledPlugin.objects.create(enabled=True, plugin=plugin)

    schedule = NewSchedule.objects.filter(plugin=enabled_plugin.plugin).first()
    assert str(schedule.recurrences) == "RRULE:FREQ=DAILY"
    assert schedule.enabled
    assert schedule.organization is None
    assert schedule.input == ""
    assert schedule.run_on is None
    assert schedule.operation is None


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
