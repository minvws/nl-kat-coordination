from django.urls import resolve, reverse
from katalogus.client import KATalogusHTTPStatusError
from reports.report_types.ipv6_report.report import IPv6Report
from reports.views.generate_report import SetupScanGenerateReportView

from octopoes.models.pagination import Paginated
from octopoes.models.types import OOIType
from tests.conftest import setup_request


def test_generate_report_setp_scan_wrong_plugin_id(
    rf,
    client_member,
    mock_katalogus_client,
    valid_time,
    mocker,
    mock_organization_view_octopoes,
    listed_hostnames,
):
    report = mocker.patch("reports.views.base")
    ipv6_report_wrong_plugin_id = IPv6Report.plugins = {
        "required": ["dns-reco"],
        "optional": [],
    }
    report.get_report_by_id.return_value = ipv6_report_wrong_plugin_id

    mock_organization_view_octopoes().list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    mock_katalogus_client.get_plugins.side_effect = KATalogusHTTPStatusError

    kwargs = {"organization_code": client_member.organization.code}
    url = reverse("generate_report_setup_scan", kwargs=kwargs)

    request = rf.get(
        url,
        {
            "observed_at": valid_time.strftime("%Y-%m-%d"),
            "ooi": "all",
            "report_type": "ipv6-report",
        },
    )
    request.resolver_match = resolve(url)

    setup_request(request, client_member.user)

    response = SetupScanGenerateReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302
    assert list(request._messages)[0].message == "404: A HTTP error occurred. Check logs for more info."
