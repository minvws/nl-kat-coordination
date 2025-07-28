from pytest_django.asserts import assertContains, assertNotContains

from plugins.models import EnabledPlugin, Plugin
from plugins.views import EnabledPluginUpdateView, EnabledPluginView, PluginListView
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
