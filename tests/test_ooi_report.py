from io import BytesIO

from django.urls import reverse, resolve
from pytest_django.asserts import assertContains
from requests import HTTPError

from octopoes.models.tree import ReferenceTree
from rocky.views.ooi_report import OOIReportView, OOIReportPDFView
from tests.conftest import setup_request

TREE_DATA = {
    "root": {
        "reference": "Finding|Network|testnetwork|KAT-000",
        "children": {"ooi": [{"reference": "Network|testnetwork", "children": {}}]},
    },
    "store": {
        "Network|testnetwork": {
            "object_type": "Network",
            "primary_key": "Network|testnetwork",
            "name": "testnetwork",
        },
        "Finding|Network|testnetwork|KAT-000": {
            "object_type": "Finding",
            "primary_key": "Finding|Network|testnetwork|KAT-000",
            "ooi": "Network|testnetwork",
            "finding_type": "KATFindingType|KAT-000",
        },
    },
}


def test_ooi_report(rf, my_user, organization, ooi_information, mock_organization_view_octopoes):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_report", kwargs=kwargs)
    request = rf.get(
        url,
        {"ooi_id": "Finding|Network|testnetwork|KAT-000"},
    )
    request.resolver_match = resolve(url)

    setup_request(request, my_user)

    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)

    response = OOIReportView.as_view()(request, **kwargs)

    assert response.status_code == 200
    assertContains(response, "testnetwork")
    assertContains(response, "Fake description...")
    assertContains(response, "Fake recommendation...")


def test_ooi_pdf_report(rf, my_user, organization, ooi_information, mock_organization_view_octopoes, mocker):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_pdf_report", kwargs=kwargs)
    request = rf.get(url, {"ooi_id": "Finding|Network|testnetwork|KAT-000"})
    request.resolver_match = resolve(url)

    setup_request(request, my_user)

    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)

    # Setup Keiko mock
    mock_keiko_client = mocker.patch("rocky.views.ooi_report.keiko_client")
    mock_keiko_client.generate_report.return_value = "fake_report_id"
    mock_keiko_client.get_report.return_value = BytesIO(b"fake_binary_pdf_content")

    response = OOIReportPDFView.as_view()(request, **kwargs)

    assert response.status_code == 200
    assert response.getvalue() == b"fake_binary_pdf_content"

    report_data_param = mock_keiko_client.generate_report.call_args[0][1]
    # Verify that the data is sent correctly to Keiko
    assert report_data_param["meta"] == {
        "total": 1,
        "total_by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 1, "recommendation": 0},
        "total_by_finding_type": {"KAT-000": 1},
        "total_finding_types": 1,
        "total_by_severity_per_finding_type": {"critical": 0, "high": 0, "medium": 0, "low": 1, "recommendation": 0},
    }
    assert report_data_param["findings_grouped"]["KAT-000"]["finding_type"]["id"] == "KAT-000"
    assert report_data_param["findings_grouped"]["KAT-000"]["list"][0]["description"] == "Fake description..."


def test_ooi_pdf_report_timeout(rf, my_user, organization, ooi_information, mock_organization_view_octopoes, mocker):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_pdf_report", kwargs=kwargs)
    request = rf.get(
        url,
        {"ooi_id": "Finding|Network|testnetwork|KAT-000"},
    )
    request.resolver_match = resolve(url)

    setup_request(request, my_user)

    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)

    # Setup Keiko mock
    mock_keiko_client = mocker.patch("rocky.views.ooi_report.keiko_client")
    mock_keiko_client.generate_report.return_value = "fake_report_id"
    # Returns None when timeout is reached, but no report was generated
    mock_keiko_client.get_report.side_effect = HTTPError

    response = OOIReportPDFView.as_view()(request, **kwargs)

    assert response.status_code == 302
    assert (
        response.url
        == reverse("ooi_report", kwargs={"organization_code": organization.code})
        + "?ooi_id=Finding%7CNetwork%7Ctestnetwork%7CKAT-000"
    )
