import pytest
from django.core.exceptions import PermissionDenied

from katalogus.models import Boefje
from katalogus.views.change_clearance_level import ChangeClearanceLevel
from tests.conftest import setup_request


def test_update_clearance_level(rf, client_member):
    boefje = Boefje.objects.create(plugin_id="test", name="test")

    with pytest.raises(PermissionDenied):
        ChangeClearanceLevel.as_view()(
            setup_request(rf.get("change_clearance_level"), client_member.user),
            organization_code=client_member.organization.code,
            plugin_type="boefje",
            plugin_id=boefje.id,
            scan_level="1",
        )
