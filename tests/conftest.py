from unittest.mock import patch

import pytest

from tools.models import Organization


@pytest.fixture
def organization():
    with patch("katalogus.client.KATalogusClientV1.create_organization"), patch(
        "octopoes.connector.octopoes.OctopoesAPIConnector.create_node"
    ):
        organization = Organization.objects.create(name="Test Organization", code="test")
    return organization


@pytest.fixture
def user(django_user_model):
    user = django_user_model.objects.create_user(email="admin@openkat.nl", password="TestTest123!!")
    user.is_verified = lambda: True
    return user


@pytest.fixture
def mock_katalogus(mocker):
    mocker.patch("tools.models.get_katalogus")


@pytest.fixture
def mock_octopoes(mocker):
    mocker.patch("tools.models.OctopoesAPIConnector")
