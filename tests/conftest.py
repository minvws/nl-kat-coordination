import pytest

from tools.models import Organization


@pytest.fixture
def organization():
    organization = Organization.objects.create(name="Test Organization", code="test")
    return organization


@pytest.fixture
def user(django_user_model):
    user = django_user_model.objects.create_user(email="admin@openkat.nl", password="TestTest123!!")
    user.is_verified = lambda: True
    return user
