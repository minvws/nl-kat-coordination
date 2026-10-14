"""Regression tests for the Rocky findings classification filters."""

import pytest
from pytest_django.asserts import assertContains
from tools.forms.findings import FindingClassificationForm

from octopoes.models.ooi.findings import Finding, RiskLevelSeverity
from octopoes.models.pagination import Paginated
from rocky.views.finding_list import FindingListView
from tests.conftest import setup_request


def test_classification_choices_follow_catalog():
    form = FindingClassificationForm()
    groups = dict(form.fields["group"].choices)
    tags = dict(form.fields["tag"].choices)

    assert len(groups) == 19  # all groups, plus the unfiltered option
    assert groups["http-security-headers"] == "HTTP Security Headers"
    assert groups["web-security"] == "Web Security"
    assert tags == {"": "All tags", "misconfiguration": "Misconfiguration"}


@pytest.mark.parametrize(
    ("params", "expected_group", "expected_tag"),
    [
        ({}, None, None),
        ({"group": "dns-security"}, "dns-security", None),
        ({"tag": "misconfiguration"}, None, "misconfiguration"),
        ({"group": "dns-security", "tag": "misconfiguration"}, "dns-security", "misconfiguration"),
        ({"group": "invalid", "tag": "misconfiguration"}, None, "misconfiguration"),
        ({"group": "dns-security", "tag": "invalid"}, "dns-security", None),
    ],
)
def test_findings_filters_reach_count_and_page(
    rf, client_member, mock_organization_view_octopoes, params, expected_group, expected_tag
):
    connector = mock_organization_view_octopoes()
    connector.list_findings.return_value = Paginated[Finding](count=0, items=[])
    response = FindingListView.as_view()(
        setup_request(rf.get("finding_list", params), client_member.user),
        organization_code=client_member.organization.code,
    )

    assert response.status_code == 200
    assert response.context_data["paginator"].count == 0
    calls = connector.list_findings.call_args_list
    assert len(calls) == 2
    assert {call.kwargs["limit"] for call in calls} == {0, 150}
    for call in calls:
        assert call.kwargs["group"] == expected_group
        assert call.kwargs["tag"] == expected_tag


def test_classification_combines_with_existing_findings_filters(rf, client_member, mock_organization_view_octopoes):
    connector = mock_organization_view_octopoes()
    connector.list_findings.return_value = Paginated[Finding](count=0, items=[])
    params = {
        "group": "dns-security",
        "tag": "misconfiguration",
        "severity": "low",
        "search": "example",
        "muted_findings": "all",
        "observed_at": "2026-01-02",
        "order_by": "finding_type",
        "sorting_order": "asc",
    }
    response = FindingListView.as_view()(
        setup_request(rf.get("finding_list", params), client_member.user),
        organization_code=client_member.organization.code,
    )

    assert response.context_data["active_filters_counter"] >= 5
    assert response.context_data["classification_filter"]["group"].value() == "dns-security"
    assert response.context_data["classification_filter"]["tag"].value() == "misconfiguration"
    for call in connector.list_findings.call_args_list:
        assert call.kwargs["group"] == "dns-security"
        assert call.kwargs["tag"] == "misconfiguration"
        assert call.kwargs["severities"] == {RiskLevelSeverity.LOW}
        assert call.kwargs["search_string"] == "example"
        assert call.kwargs["exclude_muted"] is False
        assert call.kwargs["only_muted"] is False
        assert call.kwargs["valid_time"].date().isoformat() == "2026-01-02"
        if call.kwargs["limit"] != 0:
            assert call.kwargs["order_by"] == "finding_type"
            assert call.kwargs["asc_desc"] == "asc"

    assertContains(response, 'name="group"')
    assertContains(response, 'name="tag"')
    assertContains(response, "HTTP Security Headers")
