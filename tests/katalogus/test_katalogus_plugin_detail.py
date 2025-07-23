from pytest_django.asserts import assertContains

from katalogus.models import Boefje
from katalogus.views.plugin_detail import BoefjeDetailView
from tests.conftest import setup_request


def test_plugin_detail_view(rf, superuser_member, plugins, octopoes_api_connector):
    request = setup_request(rf.get("boefje_detail"), superuser_member.user)
    boefje = Boefje.objects.get(plugin_id="dns-records")
    response = BoefjeDetailView.as_view()(
        request, organization_code=superuser_member.organization.code, plugin_id=boefje.id
    )

    assertContains(response, "DNS records")
    assertContains(response, "Produces")
    assertContains(response, "Tasks")
    assertContains(response, "Object list")
    assertContains(response, "Consumes")
    assertContains(response, boefje.description)
    assertContains(response, "Container image")
    assertContains(response, "Variants")


def test_plugin_detail_view_with_container_image(rf, superuser_member, octopoes_api_connector, plugins):
    request = setup_request(rf.get("boefje_detail"), superuser_member.user)
    dns_records = Boefje.objects.get(plugin_id="dns-records")
    dns_zone = Boefje.objects.get(plugin_id="dns-zone")
    response = BoefjeDetailView.as_view()(
        request, organization_code=superuser_member.organization.code, plugin_id=dns_records.id
    )

    assertContains(response, dns_records.name)
    assertContains(response, "Container image")
    assertContains(response, "Variants")
    assertContains(response, dns_records.name)
    assertContains(response, dns_records.oci_arguments[0])
    assertContains(response, dns_records.description)
    assertContains(response, dns_zone.name)
    assertContains(response, dns_zone.oci_arguments[0])
    assertContains(response, dns_zone.name)
    assertContains(response, "Produces")
    assertContains(response, "Tasks")
    assertContains(response, "Object list")
    assertContains(response, "Consumes")


def test_plugin_detail_view_no_consumes(rf, superuser_member, octopoes_api_connector, plugins):
    request = setup_request(rf.get("boefje_detail"), superuser_member.user)
    response = BoefjeDetailView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_id=Boefje.objects.get(plugin_id="export-to-http-api").id,
    )

    assertContains(response, "Export To HTTP API does not need any input objects.")
