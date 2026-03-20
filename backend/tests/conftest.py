import pytest
from rest_framework.test import APIClient
from tests.factories import UserFactory, SiteSettingsFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client):
    user = UserFactory()
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def site_settings():
    return SiteSettingsFactory()
