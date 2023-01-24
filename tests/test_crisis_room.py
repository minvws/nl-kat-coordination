from datetime import datetime, timezone

from django.urls import reverse, resolve
from pytest_django.asserts import assertContains

from crisis_room.views import CrisisRoomView
from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding
from octopoes.models.pagination import Paginated
from octopoes.models.types import OOIType
from tests.conftest import setup_request


def test_crisis_room(rf, my_user, organization, mock_crisis_room_octopoes):
    request = setup_request(rf.get("crisis_room"), my_user)
    request.resolver_match = resolve(reverse("crisis_room"))

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


def test_crisis_room_observed_at(rf, my_user, organization, mock_crisis_room_octopoes):
    mock_crisis_room_octopoes().list.return_value = Paginated[OOIType](count=0, items=[])

    request = setup_request(rf.get("crisis_room", {"observed_at": "2021-01-01"}), my_user)
    request.resolver_match = resolve(reverse("crisis_room"))
    response = CrisisRoomView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, "Jan 01, 2021")

    request = setup_request(rf.get("crisis_room", {"observed_at": "2021-bad-format"}), my_user)
    request.resolver_match = resolve(reverse("crisis_room"))
    response = CrisisRoomView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, datetime.now(timezone.utc).date().strftime("%b %d, %Y"))
