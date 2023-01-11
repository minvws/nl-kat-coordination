from typing import Any, Dict
from unittest.mock import patch

import pytest
from pytest_assert_utils import assert_model_attrs
from pytest_common_subject import precondition_fixture
from pytest_drf import (
    Returns200,
    Returns201,
    Returns204,
    Returns500,
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
from requests import HTTPError

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


class TestOrganizationViewSet(ViewSetTest):
    @pytest.fixture
    def organizations(self):
        with patch("katalogus.client.KATalogusClientV1.create_organization"), patch(
            "octopoes.connector.octopoes.OctopoesAPIConnector.create_node"
        ):
            return [
                Organization.objects.create(name="Test Organization 1", code="test1", tags=["tag1", "tag2"]),
                Organization.objects.create(name="Test Organization 2", code="test2"),
            ]

    organization = lambda_fixture(lambda organizations: organizations[0])

    list_url = lambda_fixture(lambda: url_for("organization-list"))
    detail_url = lambda_fixture(lambda organization: url_for("organization-detail", organization.pk))

    @pytest.fixture
    def client(self, create_drf_client, admin_user):
        client = create_drf_client(admin_user)
        # We need to set this so that the test client doesn't throw an
        # exception, but will return error in the API we can test
        client.raise_request_exception = False
        return client

    class TestList(
        UsesGetMethod,
        UsesListEndpoint,
        Returns200,
    ):
        def test_it_returns_values(self, organizations, json):
            expected = express_organizations(organizations)
            actual = json
            assert actual == expected

    class TestCreate(
        UsesPostMethod,
        UsesListEndpoint,
        Returns201,
    ):
        data = static_fixture({"name": "Test Org 3", "code": "test3", "tags": ["tag2", "tag3"]})

        initial_ids = precondition_fixture(
            lambda mock_katalogus, mock_octopoes, organizations: set(Organization.objects.values_list("id", flat=True)),
            async_=False,
        )

        def test_it_creates_new_organization(self, initial_ids, json):
            expected = initial_ids | {json["id"]}
            actual = set(Organization.objects.values_list("id", flat=True))
            assert actual == expected

        def test_it_sets_expected_attrs(self, data, json):
            organization = Organization.objects.get(pk=json["id"])

            expected = data
            assert_model_attrs(organization, expected)

        def test_it_returns_organization(self, json):
            organization = Organization.objects.get(pk=json["id"])

            expected = express_organization(organization)
            actual = json
            assert actual == expected

    class TestCreateKatalogusError(
        UsesPostMethod,
        UsesListEndpoint,
        Returns500,
    ):
        data = static_fixture({"name": "Test Org 3", "code": "test3", "tags": ["tag2", "tag3"]})

        @pytest.fixture(autouse=True)
        def mock_services(self, mocker):
            mocker.patch("katalogus.client.KATalogusClientV1.create_organization", side_effect=HTTPError("Test error"))
            mocker.patch("octopoes.connector.octopoes.OctopoesAPIConnector.create_node")

        def test_it_returns_error(self, json):
            expected = {
                "type": "server_error",
                "errors": [
                    {
                        "code": "error",
                        "detail": "Katalogus returned error creating organization: Test error",
                        "attr": None,
                    }
                ],
            }
            assert json == expected

    class TestCreateOctopoesError(
        UsesPostMethod,
        UsesListEndpoint,
        Returns500,
    ):
        data = static_fixture({"name": "Test Org 3", "code": "test3", "tags": ["tag2", "tag3"]})

        @pytest.fixture(autouse=True)
        def mock_services(self, mocker):
            mocker.patch("katalogus.client.KATalogusClientV1.create_organization")
            mocker.patch(
                "octopoes.connector.octopoes.OctopoesAPIConnector.create_node", side_effect=HTTPError("Test error")
            )

        def test_it_returns_error(self, json):
            expected = {
                "type": "server_error",
                "errors": [
                    {
                        "code": "error",
                        "detail": "Octopoes returned error creating organization: Test error",
                        "attr": None,
                    }
                ],
            }
            assert json == expected

    class TestRetrieve(
        UsesGetMethod,
        UsesDetailEndpoint,
        Returns200,
    ):
        def test_it_returns_organization(self, organization, json):
            expected = express_organization(organization)
            actual = json
            assert actual == expected

    class TestUpdate(
        UsesPatchMethod,
        UsesDetailEndpoint,
        Returns200,
    ):
        data = static_fixture(
            {
                "name": "Changed Organization",
                "code": "test4",
                "tags": ["tag3", "tag4"],
            }
        )

        # Code is read only so shouldn't change
        expected_data = {
            "name": "Changed Organization",
            "code": "test1",
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
            assert actual == expected

    class TestDestroy(
        UsesDeleteMethod,
        UsesDetailEndpoint,
        Returns204,
    ):
        initial_ids = precondition_fixture(
            lambda mock_katalogus, mock_octopoes, organizations: set(Organization.objects.values_list("id", flat=True)),
            async_=False,
        )

        def test_it_deletes_organization(self, initial_ids, organization):
            expected = initial_ids - {organization.id}
            actual = set(Organization.objects.values_list("id", flat=True))
            assert actual == expected

    class TestDestroyKatalogusError(
        UsesDeleteMethod,
        UsesDetailEndpoint,
        Returns500,
    ):
        @pytest.fixture(autouse=True)
        def mock_services(self, mocker):
            mocker.patch("katalogus.client.KATalogusClientV1.delete_organization", side_effect=HTTPError("Test error"))
            mocker.patch("octopoes.connector.octopoes.OctopoesAPIConnector.delete_node")

        def test_it_returns_error(self, json):
            expected = {
                "type": "server_error",
                "errors": [
                    {
                        "code": "error",
                        "detail": "Katalogus returned error deleting organization: Test error",
                        "attr": None,
                    }
                ],
            }
            assert json == expected

    class TestDestroyOctopoesError(
        UsesDeleteMethod,
        UsesDetailEndpoint,
        Returns500,
    ):
        @pytest.fixture(autouse=True)
        def mock_services(self, mocker):
            mocker.patch("katalogus.client.KATalogusClientV1.delete_organization")
            mocker.patch(
                "octopoes.connector.octopoes.OctopoesAPIConnector.delete_node", side_effect=HTTPError("Test error")
            )

        def test_it_returns_error(self, json):
            expected = {
                "type": "server_error",
                "errors": [
                    {
                        "code": "error",
                        "detail": "Octopoes returned error deleting organization: Test error",
                        "attr": None,
                    }
                ],
            }
            assert json == expected
