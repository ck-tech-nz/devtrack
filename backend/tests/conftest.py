import pytest
from rest_framework.test import APIClient
from tests.factories import UserFactory, SiteSettingsFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client):
    from django.contrib.auth.models import Group, Permission
    user = UserFactory()
    group, _ = Group.objects.get_or_create(name="管理员")
    group.permissions.set(
        Permission.objects.filter(content_type__app_label__in=["projects", "issues", "settings", "repos"])
    )
    user.groups.add(group)
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def site_settings():
    return SiteSettingsFactory()


@pytest.fixture
def superuser_client(api_client):
    user = UserFactory(is_superuser=True, is_staff=True)
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def regular_client(api_client):
    user = UserFactory()
    api_client.force_authenticate(user=user)
    return api_client
