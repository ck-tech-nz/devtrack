import pytest
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestProfileUpdate:
    def test_update_name_and_email(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.patch("/api/auth/me/", {
            "name": "新昵称",
            "email": "newemail@example.com",
        }, format="json")
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.name == "新昵称"
        assert user.email == "newemail@example.com"

    def test_update_avatar(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.patch("/api/auth/me/", {
            "avatar": "docker-whale",
        }, format="json")
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.avatar == "docker-whale"

    def test_update_settings(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.patch("/api/auth/me/", {
            "settings": {"theme": "dark", "sidebar_auto_collapse": True},
        }, format="json")
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.settings["theme"] == "dark"


class TestChangePassword:
    URL = "/api/auth/me/change-password/"

    def test_change_password_success(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.post(self.URL, {
            "current_password": "testpass123",
            "new_password": "NewStrongPass456!",
            "new_password_confirm": "NewStrongPass456!",
        })
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password("NewStrongPass456!")

    def test_change_password_wrong_current(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.post(self.URL, {
            "current_password": "wrongpassword",
            "new_password": "NewStrongPass456!",
            "new_password_confirm": "NewStrongPass456!",
        })
        assert response.status_code == 400
        assert "current_password" in response.data

    def test_change_password_mismatch(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        response = api_client.post(self.URL, {
            "current_password": "testpass123",
            "new_password": "NewStrongPass456!",
            "new_password_confirm": "DifferentPass789!",
        })
        assert response.status_code == 400

    def test_change_password_unauthenticated(self, api_client):
        response = api_client.post(self.URL, {
            "current_password": "x",
            "new_password": "y",
            "new_password_confirm": "y",
        })
        assert response.status_code == 401
