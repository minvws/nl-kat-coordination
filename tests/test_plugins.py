import pytest
from django.core.exceptions import PermissionDenied
from pytest_django.asserts import assertContains

from objects.models import Hostname, IPAddress, IPPort
from plugins.models import Plugin
from plugins.runner import PluginRunner
from plugins.views import PluginDeleteView, PluginListView
from tests.conftest import setup_request


def test_plugin_list(rf, superuser_member):
    Plugin.objects.create(name="testing plugins", plugin_id="testt")
    request = setup_request(rf.get("plugin_list"), superuser_member.user)
    response = PluginListView.as_view()(request)

    assert response.status_code == 200
    assertContains(response, "testing plugins")

    Plugin.objects.create(name="testing plugins 2", plugin_id="testt 2")
    response = PluginListView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, "testing plugins")
    assertContains(response, "testing plugins 2")


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


def test_arguments():
    assert Plugin(name="t", plugin_id="t").types_in_arguments() == []
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{hostname}"]).types_in_arguments() == [Hostname]
    assert Plugin(
        name="t", plugin_id="t", oci_arguments=["run {hostname} A || run {hostname} AAAA || run {hostname} CNAME"]
    ).types_in_arguments() == [Hostname]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["test", "{HOSTNAME}"]).types_in_arguments() == [Hostname]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["test", "{ipaddress}"]).types_in_arguments() == [IPAddress]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["test", "{ipaddress|hostname}"]).types_in_arguments() == [
        "ipaddress|hostname"
    ]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{ipport}", "test"]).types_in_arguments() == [IPPort]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{ipport}", "{ipport}"]).types_in_arguments() == [IPPort]
    assert set(Plugin(name="t", plugin_id="t", oci_arguments=["{ipport}", "{ipaddress}"]).types_in_arguments()) == {
        IPPort,
        IPAddress,
    }

    assert Plugin(name="t", plugin_id="t", oci_arguments=["{}"]).types_in_arguments() == []
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{file}"]).types_in_arguments() == []
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{bla}"]).types_in_arguments() == ["bla"]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{Protocol}"]).types_in_arguments() == ["Protocol"]
    assert Plugin(name="t", plugin_id="t", consumes=["type:hostname"]).types_in_arguments() == []
    assert Plugin(name="t", plugin_id="t", consumes=["type:HOSTNAME"]).types_in_arguments() == []

    assert Plugin(name="t", plugin_id="t").consumed_types() == []
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{hostname}"]).consumed_types() == [Hostname]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["test", "{HOSTNAME}"]).consumed_types() == [Hostname]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["test", "{ipaddress}"]).consumed_types() == [IPAddress]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{ipport}", "test"]).consumed_types() == [IPPort]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{}"]).consumed_types() == []
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{file}"]).consumed_types() == []
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{bla}"]).consumed_types() == ["bla"]
    assert Plugin(name="t", plugin_id="t", oci_arguments=["{Protocol}"]).consumed_types() == ["Protocol"]
    assert Plugin(name="t", plugin_id="t", consumes=["type:hostname"]).consumed_types() == [Hostname]
    assert Plugin(name="t", plugin_id="t", consumes=["type:HOSTNAME"]).consumed_types() == [Hostname]

    assert Plugin(name="t", plugin_id="t", consumes=["file:type"]).files_in_arguments() == ["type"]
    assert Plugin(name="t", plugin_id="t").files_in_arguments() == []


def test_plugin_runner_mode_4_stdin_single_and_multiple():
    Plugin.objects.create(name="testnmae", plugin_id="test-no-placeholders", oci_arguments=["No", "placeholders"])

    runner = PluginRunner()

    result = runner.run("test-no-placeholders", "example.com", cli=True)
    assert "docker run" in result

    result = runner.run("test-no-placeholders", ["example.com", "test.org"], cli=True)
    assert "docker run" in result

    result = runner.run("test-no-placeholders", None, cli=True)
    assert "docker run" in result
