from pytest_django.asserts import assertContains

from rocky.views.finding_add import FindingAddView
from tests.conftest import setup_request


def test_findings_add(rf, my_user, organization, mock_organization_view_octopoes):
    request = setup_request(rf.get("finding_add"), my_user)
    response = FindingAddView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assertContains(response, "Add Finding")
    assertContains(response, "Add finding")
