from django.urls import reverse, resolve
from pytest_django.asserts import assertContains

from crisis_room.views import CrisisRoomView
from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding
from octopoes.models.pagination import Paginated
from octopoes.models.types import OOIType
from tests.conftest import setup_request


def test_crisis_room(rf, my_user, organization, mock_crisis_room_octopoes):
    url = reverse("crisis_room")
    request = rf.get(url)
    request.resolver_match = resolve(url)

    setup_request(request, my_user)

    mock_crisis_room_octopoes().list.return_value = Paginated[OOIType](
        count=150,
        items=[
            Finding(
                finding_type=Reference.from_str("KATFindingType|KAT-0001"),
                ooi=Reference.from_str("Network|testnetwork"),
                proof="proof",
                description="description",
                reproduce="reproduce",
            )
        ]
        * 150,
    )

    response = CrisisRoomView.as_view()(request)

    assert response.status_code == 200
    assertContains(response, "1")

    assert mock_crisis_room_octopoes().list.call_count == 1
