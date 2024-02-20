from django.urls import resolve, reverse
from pytest_django.asserts import assertContains
from reports.views.aggregate_report import OOISelectionAggregateReportView, ReportTypesSelectionAggregateReportView

from octopoes.models.pagination import Paginated
from octopoes.models.types import OOIType
from tests.conftest import setup_request


def test_aggregate_report_select_oois(rf, client_member, mock_organization_view_octopoes, listed_hostnames):
    kwargs = {"organization_code": client_member.organization.code}
    url = reverse("aggregate_report_select_oois", kwargs=kwargs)
    request = rf.get(url)
    request.resolver_match = resolve(url)

    setup_request(request, client_member.user)

    mock_organization_view_octopoes().list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    response = OOISelectionAggregateReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().list_objects.call_count == 2

    assertContains(response, "Showing " + str(len(listed_hostnames)) + " of " + str(len(listed_hostnames)) + " objects")
    assertContains(response, "Hostname")
    assertContains(response, "example.com")


def test_aggregate_report_choose_report_types(
    rf, client_member, mock_organization_view_octopoes, listed_hostnames, now_formatted
):
    kwargs = {"organization_code": client_member.organization.code}
    url = reverse("aggregate_report_select_oois", kwargs=kwargs)

    request = rf.get(
        url,
        {"observed_at": now_formatted, "ooi": "all"},
    )
    request.resolver_match = resolve(url)

    setup_request(request, client_member.user)

    mock_organization_view_octopoes().list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    response = ReportTypesSelectionAggregateReportView.as_view()(
        request, organization_code=client_member.organization.code
    )

    assert response.status_code == 200

    assertContains(response, "You have selected all objects in previous step.")
