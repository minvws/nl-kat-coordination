from io import BytesIO

import pytest
from django.core.management import call_command
from django.urls import resolve, reverse
from pytest_django.asserts import assertContains
from requests import HTTPError

from octopoes.models.ooi.findings import Finding, RiskLevelSeverity
from octopoes.models.pagination import Paginated
from octopoes.models.tree import ReferenceTree
from rocky.views.ooi_report import FindingReportPDFView, OOIReportPDFView, OOIReportView
from tests.conftest import setup_request


@pytest.fixture
def tree_data():
    return {
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
            "KATFindingType|KAT-000": {
                "object_type": "KATFindingType",
                "id": "KAT-000",
                "description": "Fake description...",
                "recommendation": "Fake recommendation...",
                "risk_score": 3.9,
                "risk_severity": "low",
            },
        },
    }


def test_ooi_report(rf, client_member, mock_organization_view_octopoes, tree_data):
    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(tree_data)

    request = setup_request(rf.get("ooi_report", {"ooi_id": "Finding|Network|testnetwork|KAT-000"}), client_member.user)
    request.resolver_match = resolve(
        reverse("ooi_report", kwargs={"organization_code": client_member.organization.code})
    )
    response = OOIReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assertContains(response, "testnetwork")
    assertContains(response, "Fake description...")
    assertContains(response, "Fake recommendation...")


def test_ooi_report_missing_finding_type(rf, client_member, mock_organization_view_octopoes, tree_data):
    tree_data["store"]["Finding|Network|testnetwork|KAT-001"] = {
        "object_type": "Finding",
        "primary_key": "Finding|Network|testnetwork|KAT-001",
        "ooi": "Network|testnetwork",
        "finding_type": "KATFindingType|KAT-001",
    }
    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(tree_data)

    request = setup_request(rf.get("ooi_report", {"ooi_id": "Finding|Network|testnetwork|KAT-000"}), client_member.user)
    request.resolver_match = resolve(
        reverse("ooi_report", kwargs={"organization_code": client_member.organization.code})
    )
    response = OOIReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assertContains(response, "testnetwork")
    assertContains(response, "Fake description...")
    assertContains(response, "Fake recommendation...")


def test_ooi_pdf_report(rf, client_member, mock_organization_view_octopoes, mocker, tree_data):
    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(tree_data)

    request = setup_request(
        rf.get("ooi_pdf_report", {"ooi_id": "Finding|Network|testnetwork|KAT-000"}), client_member.user
    )
    request.resolver_match = resolve(
        reverse("ooi_report", kwargs={"organization_code": client_member.organization.code})
    )

    dt_in_filename = "2023_14_03T13_48_19_418402_+0000"
    mock_datetime = mocker.patch("rocky.keiko.datetime")
    mock_mixin_datetime = mocker.patch("rocky.views.mixins.datetime")
    mock_datetime.now().strftime.return_value = dt_in_filename
    mock_mixin_datetime.now().date.return_value = "2010-10-10"
    mock_mixin_datetime.now().strftime.return_value = dt_in_filename

    # Setup Keiko mock
    mock_keiko_client = mocker.patch("rocky.views.ooi_report.keiko_client")
    mock_keiko_client.generate_report.return_value = "fake_report_id"
    mock_keiko_client.get_report.return_value = BytesIO(b"fake_binary_pdf_content")

    response = OOIReportPDFView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assert response.getvalue() == b"fake_binary_pdf_content"
    assert (
        f"bevindingenrapport_nl_test_Finding_Network_testnetwork_KAT-000_{dt_in_filename}_{dt_in_filename}.pdf"
        in response.headers["Content-Disposition"]
    )

    report_data_param = mock_keiko_client.generate_report.call_args[0][1]
    # Verify that the data is sent correctly to Keiko
    assert report_data_param["meta"] == {
        "total": 1,
        "total_by_severity": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 1,
            "recommendation": 0,
            "pending": 0,
            "unknown": 0,
        },
        "total_by_finding_type": {"KAT-000": 1},
        "total_finding_types": 1,
        "total_by_severity_per_finding_type": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 1,
            "recommendation": 0,
            "pending": 0,
            "unknown": 0,
        },
    }
    assert report_data_param["findings_grouped"]["KAT-000"]["finding_type"]["id"] == "KAT-000"
    assert report_data_param["findings_grouped"]["KAT-000"]["list"][0]["description"] == "Fake description..."


def test_organization_pdf_report(rf, client_member, mock_organization_view_octopoes, network, finding_types, mocker):
    mock_organization_view_octopoes().list_findings.return_value = Paginated[Finding](
        count=150,
        items=[
            Finding(
                finding_type=finding_types[0].reference,
                ooi=network.reference,
                proof="proof",
                description="test description 123",
                reproduce="reproduce",
            ),
        ]
        * 150,
    )

    mock_organization_view_octopoes().load_objects_bulk.return_value = {
        network.reference: network,
        finding_types[0].reference: finding_types[0],
    }

    request = setup_request(
        rf.get("ooi_pdf_report", {"ooi_id": "Finding|Network|testnetwork|KAT-000"}), client_member.user
    )
    request.resolver_match = resolve(
        reverse("ooi_report", kwargs={"organization_code": client_member.organization.code})
    )

    dt_in_filename = "2023_14_03T13_48_19_418402_+0000"
    mock_datetime = mocker.patch("rocky.keiko.datetime")
    mock_datetime.now().strftime.return_value = dt_in_filename

    # Setup Keiko mock
    mock_keiko_client = mocker.patch("rocky.views.ooi_report.keiko_client")
    mock_keiko_client.generate_report.return_value = "fake_report_id"
    mock_keiko_client.get_report.return_value = BytesIO(b"fake_binary_pdf_content")

    response = FindingReportPDFView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assert response.getvalue() == b"fake_binary_pdf_content"
    assert f"bevindingenrapport_nl_test_{dt_in_filename}.pdf" in response.headers["Content-Disposition"]

    report_data_param = mock_keiko_client.generate_report.call_args[0][1]

    assert report_data_param["meta"] == {
        "total": 1,
        "total_by_finding_type": {"KAT-0001": 1},
        "total_by_severity": {
            "critical": 1,
            "high": 0,
            "low": 0,
            "medium": 0,
            "recommendation": 0,
            "pending": 0,
            "unknown": 0,
        },
        "total_by_severity_per_finding_type": {
            "critical": 1,
            "high": 0,
            "low": 0,
            "medium": 0,
            "recommendation": 0,
            "pending": 0,
            "unknown": 0,
        },
        "total_finding_types": 1,
    }
    assert report_data_param["findings_grouped"]["KAT-0001"]["finding_type"]["id"] == "KAT-0001"
    assert report_data_param["findings_grouped"]["KAT-0001"]["list"][0]["description"] == "test description 123"


def test_pdf_report_command(tmp_path, client_member, network, finding_types, mocker):
    mock_organization_view_octopoes = mocker.patch("tools.management.commands.generate_report.OctopoesAPIConnector")
    mock_organization_view_octopoes().list_findings.return_value = Paginated[Finding](
        count=3,
        items=[
            Finding(
                finding_type=finding_types[0].reference,
                ooi=network.reference,
                proof="proof",
                description="test description 123",
                reproduce="reproduce",
            ),
            Finding(
                finding_type=finding_types[1].reference,
                ooi=network.reference,
                proof="proof",
                description="test description 123",
                reproduce="reproduce",
            ),
            Finding(
                finding_type=finding_types[2].reference,
                ooi=network.reference,
                proof="proof",
                description="test description 123",
                reproduce="reproduce",
            ),
        ],
    )

    mock_organization_view_octopoes().load_objects_bulk.return_value = {
        network.reference: network,
        finding_types[0].reference: finding_types[0],
        finding_types[1].reference: finding_types[1],
        finding_types[2].reference: finding_types[2],
    }

    dt_in_filename = "2023_14_03T13_48_19_418402_+0000"
    mock_datetime = mocker.patch("rocky.keiko.datetime")
    mock_datetime.now().strftime.return_value = dt_in_filename

    # Setup Keiko mock
    mock_keiko_client = mocker.patch("tools.management.commands.generate_report.keiko_client")
    mock_keiko_client.generate_report.return_value = "fake_report_id"
    mock_keiko_client.get_report.return_value = BytesIO(b"fake_binary_pdf_content")

    tmp_file = tmp_path / "test.pdf"
    call_command(
        "generate_report", code=client_member.organization.code, output=tmp_file, min_severity=RiskLevelSeverity.HIGH
    )

    assert tmp_file.exists()
    assert tmp_file.read_text() == "fake_binary_pdf_content"

    report_data_param = mock_keiko_client.generate_report.call_args[0][1]

    assert report_data_param["meta"] == {
        "total": 2,
        "total_by_finding_type": {"KAT-0001": 1, "KAT-0002": 1},
        "total_by_severity": {
            "critical": 2,
            "high": 0,
            "low": 0,
            "medium": 0,
            "recommendation": 0,
            "pending": 0,
            "unknown": 0,
        },
        "total_by_severity_per_finding_type": {
            "critical": 2,
            "high": 0,
            "low": 0,
            "medium": 0,
            "recommendation": 0,
            "pending": 0,
            "unknown": 0,
        },
        "total_finding_types": 2,
    }


def test_ooi_pdf_report_timeout(rf, client_member, mock_organization_view_octopoes, mocker, tree_data):
    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(tree_data)

    request = setup_request(
        rf.get("ooi_pdf_report", {"ooi_id": "Finding|Network|testnetwork|KAT-000"}), client_member.user
    )
    request.resolver_match = resolve(
        reverse("ooi_report", kwargs={"organization_code": client_member.organization.code})
    )

    mock_keiko_session = mocker.patch("rocky.views.ooi_report.keiko_client.session")
    mock_keiko_session.post.side_effect = HTTPError

    response = OOIReportPDFView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302
    assert (
        response.url
        == reverse("ooi_report", kwargs={"organization_code": client_member.organization.code})
        + "?ooi_id=Finding%7CNetwork%7Ctestnetwork%7CKAT-000"
    )
