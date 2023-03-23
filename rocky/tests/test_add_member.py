import pytest
from pytest_django.asserts import assertContains
from tests.conftest import setup_request
from rocky.views.organization_member_add import OrganizationMemberAddView
from tools.models import GROUP_ADMIN, GROUP_REDTEAM, GROUP_CLIENT


def test_add_existing_member(rf, admin_member, redteam_member):
    """
    Adding an existing member will also mean that all credentials
    are copied to the other org and not overriden by values added in form by mistake.
    """
    group = redteam_member.user.groups.all().values_list("name", flat=True)
    request = setup_request(
        rf.post(
            "organization_member_add",
            {
                "account_type": "clients",
                "name": redteam_member.user.full_name + "additional name",
                "email": redteam_member.user.email,
                "password": redteam_member.user.password + "extra password",
            },
        ),
        admin_member.user,
    )
    OrganizationMemberAddView.as_view()(request, organization_code=admin_member.organization.code, pk=redteam_member.id)

    redteam_member.refresh_from_db()
    assert GROUP_REDTEAM in group
