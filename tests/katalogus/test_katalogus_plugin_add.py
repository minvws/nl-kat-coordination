from django.urls import reverse
from pytest_django.asserts import assertContains, assertNotContains

from katalogus.models import Boefje
from katalogus.views.plugin_settings_add import PluginSettingsAddView
from tests.conftest import setup_request


def test_plugin_settings_add_view(rf, superuser_member, plugins):
    request = setup_request(rf.get("plugin_settings_add"), superuser_member.user)
    response = PluginSettingsAddView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_type="boefje",
        plugin_id=Boefje.objects.get(plugin_id="censys").id,
    )

    assertContains(response, "Censys")
    assertContains(response, "Add setting")
    assertContains(response, "CENSYS_API_ID")
    assertContains(response, "CENSYS_API_SECRET")
    assertContains(response, "Add settings and enable boefje")


def test_plugin_settings_add_view_no_required(rf, superuser_member, dns_records):
    request = setup_request(rf.get("plugin_settings_add"), superuser_member.user)
    response = PluginSettingsAddView.as_view()(
        request, organization_code=superuser_member.organization.code, plugin_type="boefje", plugin_id=dns_records.id
    )

    assertContains(response, "DNS records")
    assertContains(response, "Add setting")
    assertContains(response, "REMOTE_NS")
    assertContains(response, "RECORD_TYPES")
    assertContains(response, "Add settings and enable boefje")


def test_plugin_settings_add(rf, superuser_member, plugins):
    request = setup_request(
        rf.post("plugin_settings_add", data={"CENSYS_API_ID": "A", "CENSYS_API_SECRET": "B"}), superuser_member.user
    )
    response = PluginSettingsAddView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_type="boefje",
        plugin_id=Boefje.objects.get(plugin_id="censys").id,
    )

    assert response.status_code == 302
    assert list(request._messages).pop().message == "Added settings for 'Censys'"


def test_plugin_settings_add_no_required(rf, superuser_member, dns_records):
    request = setup_request(rf.post("plugin_settings_add", data={"RECORD_TYPES": "123"}), superuser_member.user)
    response = PluginSettingsAddView.as_view()(
        request, organization_code=superuser_member.organization.code, plugin_type="boefje", plugin_id=dns_records.id
    )

    assert response.status_code == 302
    assert list(request._messages).pop().message == "Added settings for 'DNS records'"


def test_plugin_settings_add_wrong_property_but_required(rf, superuser_member, plugins):
    request = setup_request(rf.post("plugin_settings_add", data={"WRONG_PROPERTY": 123}), superuser_member.user)
    response = PluginSettingsAddView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_type="boefje",
        plugin_id=Boefje.objects.get(plugin_id="censys").id,
    )
    assertContains(response, "Error")
    assertContains(response, "This field is required.")


def test_plugin_settings_add_string_too_long(rf, superuser_member, dns_records):
    request = setup_request(rf.post("plugin_settings_add", data={"REMOTE_NS": 46 * "a"}), superuser_member.user)
    response = PluginSettingsAddView.as_view()(
        request, organization_code=superuser_member.organization.code, plugin_type="boefje", plugin_id=dns_records.id
    )
    assertContains(response, "Ensure this value has at most 45 characters (it has 46).")
    assertNotContains(response, "Enter a whole number.")


def test_plugin_settings_add_error_message_about_integer_for_string_type(rf, superuser_member, plugins):
    request = setup_request(rf.post("plugin_settings_add", data={"TIMEOUT": "abc"}), superuser_member.user)
    response = PluginSettingsAddView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_type="boefje",
        plugin_id=Boefje.objects.get(plugin_id="dns-bind-version").id,
    )

    assertContains(response, "Error")
    assertContains(response, "Enter a whole number.")


def test_plugin_settings_add_error_message_about_integer_too_small(rf, superuser_member, plugins):
    request = setup_request(rf.post("plugin_settings_add", data={"TIMEOUT": -1}), superuser_member.user)
    response = PluginSettingsAddView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_type="boefje",
        plugin_id=Boefje.objects.get(plugin_id="dns-bind-version").id,
    )

    assertContains(response, "Error")
    assertContains(response, "-1 is less than the minimum of 0")


def test_plugin_settings_add_error_message_about_integer_too_big(rf, superuser_member, plugins):
    request = setup_request(rf.post("plugin_settings_add", data={"TOP_PORTS": 1000000}), superuser_member.user)
    response = PluginSettingsAddView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_type="boefje",
        plugin_id=Boefje.objects.get(plugin_id="nmap").id,
    )

    assertContains(response, "Error")
    assertContains(response, "1000000 is greater than the maximum of 65535")


def test_plugin_single_settings_add_view_no_schema(rf, superuser_member, plugins):
    request = setup_request(rf.post("plugin_settings_add", data={"boefje_id": 123}), superuser_member.user)
    boefje = Boefje.objects.get(plugin_id="kat-finding-types")
    response = PluginSettingsAddView.as_view()(
        request, organization_code=superuser_member.organization.code, plugin_type="boefje", plugin_id=boefje.id
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "boefje_detail", kwargs={"organization_code": superuser_member.organization.code, "plugin_id": boefje.id}
    )
    assert list(request._messages).pop().message == "Trying to add settings to boefje without schema"
