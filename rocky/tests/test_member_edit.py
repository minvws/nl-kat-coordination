import pytest
from django.contrib.auth.models import Permission
from pytest_django.asserts import assertContains, assertNotContains

from rocky.views.organization_detail import OrganizationDetailView
from rocky.views.organization_edit import OrganizationEditView
from rocky.views.organization_list import OrganizationListView
from tests.conftest import setup_request
from tools.models import OrganizationMember
from rocky.views.organization_detail import OrganizationDetailView


def test_member_edit_forbidden(rf, my_user, organization):
    """
    This test will check if a member without access rights can edit another member from the edit page.
    """
    request = setup_request(rf.get("organization_detail"), my_user)
    response = OrganizationDetailView.as_view()(request, organization_code=organization.code)
