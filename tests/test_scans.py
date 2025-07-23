from pytest_django.asserts import assertContains

from katalogus.models import Boefje
from openkat.views.scans import ScanListView
from tests.conftest import setup_request


def test_katalogus_plugin_listing(client_member, katalogus_client, rf):
    boefje = Boefje.objects.create(plugin_id="test", name="My test Boefje test_katalogus_plugin_listing")

    katalogus_client.enable_boefje_by_id(client_member.organization.code, boefje.id)

    request = setup_request(rf.get("scan_list"), client_member.user)
    response = ScanListView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assertContains(response, "Boefjes")
    assertContains(response, boefje.name)
