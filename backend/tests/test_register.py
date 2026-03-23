import pytest
from django.contrib.auth import get_user_model
from apps.users.avatar_choices import AVATAR_CHOICES

pytestmark = pytest.mark.django_db
User = get_user_model()


class TestRegister:
    URL = "/api/auth/register/"

    def test_register_success(self, api_client):
        response = api_client.post(self.URL, {
            "username": "newuser",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "name": "新用户",
            "email": "new@example.com",
            "avatar": "robot",
        })
        assert response.status_code == 201
        assert response.data["username"] == "newuser"
        assert response.data["name"] == "新用户"
        user = User.objects.get(username="newuser")
        assert user.is_active is False
        assert user.avatar == "robot"

    def test_register_random_avatar(self, api_client):
        response = api_client.post(self.URL, {
            "username": "randomavatar",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        assert response.status_code == 201
        user = User.objects.get(username="randomavatar")
        assert user.avatar in AVATAR_CHOICES

    def test_register_duplicate_username(self, api_client):
        User.objects.create_user(username="taken", password="pass")
        response = api_client.post(self.URL, {
            "username": "taken",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        assert response.status_code == 400
        assert "username" in response.data

    def test_register_password_mismatch(self, api_client):
        response = api_client.post(self.URL, {
            "username": "mismatch",
            "password": "StrongPass123!",
            "password_confirm": "DifferentPass456!",
        })
        assert response.status_code == 400
        assert "password_confirm" in response.data

    def test_register_weak_password(self, api_client):
        response = api_client.post(self.URL, {
            "username": "weakpass",
            "password": "123",
            "password_confirm": "123",
        })
        assert response.status_code == 400

    def test_register_invalid_avatar(self, api_client):
        response = api_client.post(self.URL, {
            "username": "badavatar",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "avatar": "nonexistent",
        })
        assert response.status_code == 400
        assert "avatar" in response.data

    def test_inactive_user_cannot_login(self, api_client):
        api_client.post(self.URL, {
            "username": "inactive",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        response = api_client.post("/api/auth/login/", {
            "username": "inactive",
            "password": "StrongPass123!",
        })
        assert response.status_code == 401
