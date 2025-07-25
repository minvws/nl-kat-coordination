from plugins.models import EnabledPlugin, Plugin
from plugins.views import EnabledPluginUpdateView, EnabledPluginView
from tests.conftest import setup_request


def test_enable_plugins(rf, superuser_member):
    plugin = Plugin.objects.create(name="test", plugin_id="testt")
    request = setup_request(
        rf.post("plugin_enabled", {"organization": "", "enabled": True, "plugin": plugin.id}), superuser_member.user
    )
    response = EnabledPluginView.as_view()(request)

    assert response.status_code == 302
    enabled_plugin = EnabledPlugin.objects.first()

    assert enabled_plugin
    assert enabled_plugin.enabled is True

    request = setup_request(
        rf.post("plugin_enabled", {"organization": "", "enabled": False, "plugin": plugin.id}), superuser_member.user
    )
    response = EnabledPluginUpdateView.as_view()(request, pk=enabled_plugin.id)
    assert response.status_code == 302

    assert EnabledPlugin.objects.count() == 1
    enabled_plugin.refresh_from_db()
    assert enabled_plugin.enabled is False
