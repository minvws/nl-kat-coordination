import json

from django.urls import reverse
from pytest_django.asserts import assertContains

from katalogus.models import Boefje, BoefjeConfig
from katalogus.views.plugin_settings_delete import PluginSettingsDeleteView
from tests.conftest import setup_request


def test_plugin_settings_delete_view(rf, superuser_member, plugins):
    request = setup_request(rf.get("plugin_settings_delete"), superuser_member.user)
    response = PluginSettingsDeleteView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_type="boefje",
        plugin_id=Boefje.objects.get(plugin_id="dns-records").id,
        setting_name="REMOTE_NS",
    )

    assertContains(response, "DNS records")
    assertContains(response, "Delete settings")


def test_plugin_settings_delete(rf, superuser_member, organization, plugins):
    request = setup_request(rf.post("plugin_settings_delete"), superuser_member.user)
    boefje = Boefje.objects.get(plugin_id="dns-records")
    BoefjeConfig.objects.create(organization=organization, boefje=boefje, settings=json.dumps({"REMOTE_NS": "A"}))

    response = PluginSettingsDeleteView.as_view()(
        request, organization_code=superuser_member.organization.code, plugin_type="boefje", plugin_id=boefje.id
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "boefje_detail", kwargs={"organization_code": superuser_member.organization.code, "plugin_id": boefje.id}
    )
    assert list(request._messages).pop().message == "Settings for plugin DNS records successfully deleted."


def test_plugin_settings_delete_no_settings_present(rf, superuser_member, plugins):
    request = setup_request(rf.post("plugin_settings_delete"), superuser_member.user)
    boefje = Boefje.objects.get(plugin_id="dns-records")
    response = PluginSettingsDeleteView.as_view()(
        request, organization_code=superuser_member.organization.code, plugin_type="boefje", plugin_id=boefje.id
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "boefje_detail", kwargs={"organization_code": superuser_member.organization.code, "plugin_id": boefje.id}
    )
    assert list(request._messages).pop().message == "Plugin DNS records has no settings."
