from typing import Any, Dict

import pytest
from pytest_assert_utils import assert_model_attrs
from pytest_common_subject import precondition_fixture
from pytest_drf import (
    AsUser,
    Returns200,
    Returns201,
    Returns204,
    UsesGetMethod,
    UsesDeleteMethod,
    UsesDetailEndpoint,
    UsesListEndpoint,
    UsesPatchMethod,
    UsesPostMethod,
    ViewSetTest,
)
from pytest_drf.util import pluralized, url_for
from pytest_lambda import lambda_fixture, static_fixture

from tools.models import Organization


pytestmark = pytest.mark.django_db


def express_organization(organization: Organization) -> Dict[str, Any]:
    return {
        "id": organization.id,
        "name": organization.name,
        "code": organization.code,
        "tags": [tag for tag in organization.tags.all()],
    }


express_organizations = pluralized(express_organization)


class TestOrganizationViewSet(ViewSetTest, AsUser("admin_user")):
    list_url = lambda_fixture(lambda: url_for("organization-list"))
    detail_url = lambda_fixture(lambda organization: url_for("organization-detail", organization.pk))

    organizations = lambda_fixture(
        lambda: [
            Organization.objects.create(name="Test Organistion", code="test", tags=["tag1", "tag2"]),
            Organization.objects.create(name="Test Organization 2", code="test2"),
        ],
    )
    organization = lambda_fixture(lambda organizations: organizations[0])

    class TestList(
        UsesGetMethod,
        UsesListEndpoint,
        Returns200,
    ):
        def test_it_returns_values(self, organizations, json):
            expected = express_organizations(organizations)
            actual = json
            assert expected == actual

    class TestCreate(
        UsesPostMethod,
        UsesListEndpoint,
        Returns201,
    ):
        data = static_fixture({"name": "Test Org 3", "code": "test3", "tags": ["tag2", "tag3"]})

        initial_ids = precondition_fixture(
            lambda organizations: set(Organization.objects.values_list("id", flat=True)), async_=False
        )

        def test_it_creates_new_organization(self, initial_ids, json):
            expected = initial_ids | {json["id"]}
            actual = set(Organization.objects.values_list("id", flat=True))
            assert expected == actual

        def test_it_sets_expected_attrs(self, data, json):
            organization = Organization.objects.get(pk=json["id"])

            expected = data
            assert_model_attrs(organization, expected)

        def test_it_returns_organization(self, json):
            organization = Organization.objects.get(pk=json["id"])

            expected = express_organization(organization)
            actual = json
            assert expected == actual

    class TestRetrieve(
        UsesGetMethod,
        UsesDetailEndpoint,
        Returns200,
    ):
        def test_it_returns_organization(self, organization, json):
            expected = express_organization(organization)
            actual = json
            assert expected == actual

    class TestUpdate(
        UsesPatchMethod,
        UsesDetailEndpoint,
        Returns200,
    ):
        data = static_fixture(
            {
                "name": "Changed Orgazisation",
                "code": "test4",
                "tags": ["tag3", "tag4"],
            }
        )

        # Code is read only so shouldn't change
        expected_data = {
            "name": "Changed Orgazisation",
            "code": "test",
        }

        def test_it_sets_expected_attrs(self, organization):
            # We must tell Django to grab fresh data from the database, or we'll
            # see our stale initial data and think our endpoint is broken!
            organization.refresh_from_db()

            assert_model_attrs(organization, self.expected_data)
            assert {str(tag) for tag in organization.tags.all()} == {"tag3", "tag4"}

        def test_it_returns_organization(self, organization, json):
            organization.refresh_from_db()

            expected = express_organization(organization)
            actual = json
            assert expected == actual

    class TestDestroy(
        UsesDeleteMethod,
        UsesDetailEndpoint,
        Returns204,
    ):
        initial_ids = precondition_fixture(
            lambda organizations: set(Organization.objects.values_list("id", flat=True)), async_=False
        )

        def test_it_deletes_organization(self, initial_ids, organization):
            expected = initial_ids - {organization.id}
            actual = set(Organization.objects.values_list("id", flat=True))
            assert expected == actual
