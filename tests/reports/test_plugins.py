from django.urls import resolve, reverse

from katalogus.client import KATalogusError
from octopoes.models.pagination import Paginated
from octopoes.models.types import OOIType
from reports.views.generate_report import SetupScanGenerateReportView
from tests.conftest import setup_request


def test_generate_report_setup_scan_wrong_plugin_id(
    rf, client_member, valid_time, mocker, octopoes_api_connector, listed_hostnames
):
    katalogus_client = mocker.patch("account.mixins.OrganizationView.get_katalogus")()
    octopoes_api_connector.list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )
    katalogus_client.get_plugins.side_effect = KATalogusError("Unexpected error. Check the logs for further details.")

    kwargs = {"organization_code": client_member.organization.code}
    url = reverse("generate_report_setup_scan", kwargs=kwargs)

    request = rf.post(url, {"observed_at": valid_time.strftime("%Y-%m-%d"), "ooi": "all", "report_type": "ipv6-report"})
    request.resolver_match = resolve(url)

    setup_request(request, client_member.user)
    response = SetupScanGenerateReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 307
    assert list(request._messages)[0].message == "Unexpected error. Check the logs for further details."
