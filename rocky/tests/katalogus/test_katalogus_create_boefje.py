from katalogus.views.boefje_setup import BoefjeSetupView
from pytest_django.asserts import assertContains

from tests.conftest import setup_request


def test_boefje_setup(rf, superuser_member):
    request = setup_request(rf.get("boefje_setup"), superuser_member.user)
    response = BoefjeSetupView.as_view()(request, organization_code=superuser_member.organization.code)

    assert response.status_code == 200
    assertContains(response, "Boefje setup")
    assertContains(response, "Container image")
    assertContains(response, "Name")
    assertContains(response, "Description")
    assertContains(response, "Arguments")
    assertContains(response, "JSON Schema")
    assertContains(response, "Input object type")
    assertContains(response, "Output mimetypes")
    assertContains(response, "Clearance level")
    assertContains(response, "Create variant")
