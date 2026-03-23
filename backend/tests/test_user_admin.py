import pytest
from django.contrib.auth.models import Group
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestAdminUserList:
    def test_list_users_with_admin(self, auth_client):
        UserFactory.create_batch(3)
        response = auth_client.get("/api/users/")
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        assert len(results) >= 4
        first = results[0]
        assert "is_active" in first
        assert "date_joined" in first
        assert "groups" in first

    def test_list_users_without_permission(self, regular_client):
        response = regular_client.get("/api/users/")
        assert response.status_code == 403

    def test_list_users_unauthenticated(self, api_client):
        response = api_client.get("/api/users/")
        assert response.status_code == 401


class TestAdminUserDetail:
    def test_get_user_detail(self, auth_client):
        user = UserFactory(name="李四", avatar="robot")
        response = auth_client.get(f"/api/users/{user.id}/")
        assert response.status_code == 200
        assert response.data["name"] == "李四"
        assert response.data["avatar"] == "robot"
        assert "is_active" in response.data

    def test_update_user(self, auth_client):
        user = UserFactory(name="旧名字")
        response = auth_client.patch(f"/api/users/{user.id}/", {
            "name": "新名字",
            "email": "new@example.com",
        }, format="json")
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.name == "新名字"

    def test_activate_user(self, auth_client):
        user = UserFactory(is_active=False)
        response = auth_client.patch(f"/api/users/{user.id}/", {
            "is_active": True,
        }, format="json")
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_active is True

    def test_deactivate_user(self, auth_client):
        user = UserFactory(is_active=True)
        response = auth_client.patch(f"/api/users/{user.id}/", {
            "is_active": False,
        }, format="json")
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_active is False

    def test_assign_groups(self, auth_client):
        user = UserFactory()
        Group.objects.create(name="测试组")
        response = auth_client.patch(f"/api/users/{user.id}/", {
            "groups": ["测试组"],
        }, format="json")
        assert response.status_code == 200
        assert "测试组" in list(user.groups.values_list("name", flat=True))

    def test_assign_nonexistent_group(self, auth_client):
        user = UserFactory()
        response = auth_client.patch(f"/api/users/{user.id}/", {
            "groups": ["不存在的组"],
        }, format="json")
        assert response.status_code == 400

    def test_update_without_permission(self, regular_client):
        user = UserFactory()
        response = regular_client.patch(f"/api/users/{user.id}/", {
            "name": "hack",
        }, format="json")
        assert response.status_code == 403
