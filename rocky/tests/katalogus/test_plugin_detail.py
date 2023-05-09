from katalogus.client import parse_plugin
from katalogus.views.plugin_detail import PluginDetailView
from pytest_django.asserts import assertContains

from tests.conftest import setup_request


def test_plugin_detail_start_scan_redteamer_no_clearance(
    rf, redteam_member, mock_mixins_katalogus, mock_organization_view_octopoes, mock_scheduler, hostname
):
    mock_organization_view_octopoes().get.return_value = hostname
    mock_mixins_katalogus().get_plugin.return_value = parse_plugin(
        {
            "id": "dns-records",
            "type": "boefje",
            "name": "DnsRecords",
            "description": "Fetch the DNS record(s) of a hostname",
            "repository_id": "test-repository",
            "scan_level": 1,
            "consumes": ["Hostname"],
            "produces": ["IPAddressV4"],
            "enabled": True,
        }
    )

    request = setup_request(
        rf.post(
            "plugin_detail",
            data={
                "ooi": "Hostname|testnetwork|openkat.nl",
                "boefje_id": "dns-records",
            },
        ),
        redteam_member.user,
    )
    redteam_member.acknowledged_clearance_level = 0
    redteam_member.save()

    response = PluginDetailView.as_view()(
        request,
        organization_code=redteam_member.organization.code,
        plugin_type="boefje",
        plugin_id="dns-records",
    )

    assert response.status_code == 200
    assertContains(response, "You do not have clearanace to start scan.")
