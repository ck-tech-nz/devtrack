import pytest
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestLogin:
    def test_login_success(self, api_client):
        user = UserFactory(username="zhangsan")
        response = api_client.post("/api/auth/login/", {
            "username": "zhangsan",
            "password": "testpass123",
        })
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_wrong_password(self, api_client):
        UserFactory(username="zhangsan")
        response = api_client.post("/api/auth/login/", {
            "username": "zhangsan",
            "password": "wrong",
        })
        assert response.status_code == 401

    def test_refresh_token(self, api_client):
        user = UserFactory(username="zhangsan")
        login = api_client.post("/api/auth/login/", {
            "username": "zhangsan",
            "password": "testpass123",
        })
        response = api_client.post("/api/auth/refresh/", {
            "refresh": login.data["refresh"],
        })
        assert response.status_code == 200
        assert "access" in response.data


class TestMe:
    def test_me_authenticated(self, api_client):
        user = UserFactory(username="zhangsan", name="张三", email="zs@example.com")
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/auth/me/")
        assert response.status_code == 200
        assert response.data["name"] == "张三"
        assert response.data["email"] == "zs@example.com"
        assert "groups" in response.data
        assert "permissions" in response.data

    def test_me_unauthenticated(self, api_client):
        response = api_client.get("/api/auth/me/")
        assert response.status_code == 401

    def test_me_includes_group_names(self, api_client):
        from django.contrib.auth.models import Group
        user = UserFactory()
        group = Group.objects.create(name="前端开发")
        user.groups.add(group)
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/auth/me/")
        assert "前端开发" in response.data["groups"]
