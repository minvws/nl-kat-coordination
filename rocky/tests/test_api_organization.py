from typing import Any
from unittest.mock import patch

import pytest
from django.urls import reverse
from httpx import HTTPError
from pytest_assert_utils import assert_model_attrs
from pytest_common_subject import precondition_fixture
from pytest_drf import (
    APIViewTest,
    Returns200,
    Returns201,
    Returns204,
    Returns409,
    Returns500,
    UsesDeleteMethod,
    UsesDetailEndpoint,
    UsesGetMethod,
    UsesListEndpoint,
    UsesPatchMethod,
    UsesPostMethod,
    ViewSetTest,
)
from pytest_drf.util import pluralized, url_for
from pytest_lambda import lambda_fixture, static_fixture
from tools.models import Organization

pytestmark = pytest.mark.django_db


def express_organization(organization: Organization) -> dict[str, Any]:
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
        with patch("katalogus.client.KATalogusClientV1"), patch("tools.models.OctopoesAPIConnector"):
            return [
                Organization.objects.create(name="Test Organization 1", code="test1", tags=["tag1", "tag2"]),
                Organization.objects.create(name="Test Organization 2", code="test2"),
            ]

    organization = lambda_fixture(lambda organizations: organizations[0])

    list_url = lambda_fixture(lambda: url_for("organization-list"))
    detail_url = lambda_fixture(lambda organization: url_for("organization-detail", organization.pk))

    client = lambda_fixture("drf_admin_client")

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
            lambda mock_models_katalogus, mock_models_octopoes, organizations: set(
                Organization.objects.values_list("id", flat=True)
            ),
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
            mocker.patch("tools.models.KATalogusClientV1.organization_exists", return_value=False)
            mocker.patch("tools.models.KATalogusClientV1.create_organization", side_effect=HTTPError("Test error"))
            mocker.patch("tools.models.KATalogusClientV1.health")
            mocker.patch("tools.models.OctopoesAPIConnector.root_health")
            mocker.patch("tools.models.OctopoesAPIConnector.create_node")

        def test_it_returns_error(self, json):
            expected = {
                "type": "server_error",
                "errors": [
                    {
                        "code": "error",
                        "detail": "Failed creating organization in the Katalogus",
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
            mocker.patch("tools.models.KATalogusClientV1.health")
            mocker.patch("tools.models.KATalogusClientV1.organization_exists", return_value=False)
            mocker.patch("tools.models.KATalogusClientV1.create_organization")
            mocker.patch("tools.models.KATalogusClientV1.delete_organization")  # Needed because of the "rollback"
            mocker.patch("tools.models.OctopoesAPIConnector.root_health")
            mocker.patch("tools.models.OctopoesAPIConnector.create_node", side_effect=HTTPError("Test error"))

        def test_it_returns_error(self, json):
            expected = {
                "type": "server_error",
                "errors": [
                    {
                        "code": "error",
                        "detail": "Failed creating organization in Octopoes",
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

        @pytest.fixture(autouse=True)
        def mock_services(self, mocker):
            mocker.patch("tools.models.KATalogusClientV1.health")
            mocker.patch("tools.models.KATalogusClientV1.organization_exists", return_value=False)
            mocker.patch("tools.models.KATalogusClientV1.create_organization")
            mocker.patch("tools.models.KATalogusClientV1.delete_organization")  # Needed because of the "rollback"
            mocker.patch("tools.models.OctopoesAPIConnector")

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
            lambda mock_models_katalogus, mock_models_octopoes, organizations: set(
                Organization.objects.values_list("id", flat=True)
            ),
            async_=False,
        )

        def test_it_deletes_organization(self, initial_ids, organization, log_output):
            expected = initial_ids - {organization.id}
            actual = set(Organization.objects.values_list("id", flat=True))
            assert actual == expected

            organization_created_log = log_output.entries[-2]
            assert organization_created_log["event"] == "%s %s deleted"
            assert organization_created_log["object"] == "Test Organization 1"
            assert organization_created_log["object_type"] == "Organization"

    class TestDestroyKatalogusError(
        UsesDeleteMethod,
        UsesDetailEndpoint,
        Returns500,
    ):
        @pytest.fixture(autouse=True)
        def mock_services(self, mocker):
            mocker.patch("tools.models.KATalogusClientV1.health")
            mocker.patch("tools.models.KATalogusClientV1.delete_organization", side_effect=HTTPError("Test error"))
            mocker.patch("tools.models.OctopoesAPIConnector")

        def test_it_returns_error(self, json):
            expected = {
                "type": "server_error",
                "errors": [
                    {
                        "code": "error",
                        "detail": "Failed deleting organization in the Katalogus",
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
            mocker.patch("tools.models.KATalogusClientV1.health")
            mocker.patch("tools.models.KATalogusClientV1.delete_organization")
            mocker.patch("tools.models.OctopoesAPIConnector.root_health")
            mocker.patch("tools.models.OctopoesAPIConnector.delete_node", side_effect=HTTPError("Test error"))

        def test_it_returns_error(self, json):
            expected = {
                "type": "server_error",
                "errors": [
                    {
                        "code": "error",
                        "detail": "Failed deleting organization in Octopoes",
                        "attr": None,
                    }
                ],
            }
            assert json == expected


class TestGetIndemnification(APIViewTest, UsesGetMethod, Returns200):
    # The superuser_member fixture creates the indemnification
    url = lambda_fixture(
        lambda organization, superuser_member: reverse("organization-indemnification", args=[organization.pk])
    )
    client = lambda_fixture("drf_admin_client")

    def test_it_returns_indemnification(self, json, superuser_member):
        expected = {"indemnification": True, "user": superuser_member.user.id}
        assert json == expected


class TestIndemnificationDoesNotExist(APIViewTest, UsesGetMethod, Returns200):
    url = lambda_fixture(lambda organization: reverse("organization-indemnification", args=[organization.pk]))
    client = lambda_fixture("drf_admin_client")

    def test_it_returns_no_indemnification(self, json):
        expected = {"indemnification": False, "user": None}
        assert json == expected


class TestSetIndemnification(APIViewTest, UsesPostMethod, Returns201):
    url = lambda_fixture(lambda organization: reverse("organization-indemnification", args=[organization.pk]))
    client = lambda_fixture("drf_admin_client")

    def test_it_sets_indemnification(self, json, admin_user):
        expected = {"indemnification": True, "user": admin_user.id}
        assert json == expected


class TestIndemnificationAlreadyExists(APIViewTest, UsesPostMethod, Returns409):
    # The superuser_member fixture creates the indemnification
    url = lambda_fixture(
        lambda organization, superuser_member: reverse("organization-indemnification", args=[organization.pk])
    )
    client = lambda_fixture("drf_admin_client")

    def test_it_returns_indemnification(self, json, superuser_member):
        expected = {"indemnification": True, "user": superuser_member.user.id}
        assert json == expected
