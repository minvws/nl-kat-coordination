from django.urls import reverse, resolve
from pytest_django.asserts import assertContains

from katalogus.views import KATalogusView
from tests.conftest import setup_request


def test_katalogus_plugin_listing(my_user, rf, organization, mocker):
    mocker.patch("katalogus.client.KATalogusClientV1")

    kwargs = {"organization_code": organization.code}
    url = reverse("katalogus", kwargs=kwargs)
    request = rf.get(url)
    setup_request(request, my_user)
    request.resolver_match = resolve(url)
    response = KATalogusView.as_view()(request, **kwargs)
    assertContains(response, "KAT-alogus")
