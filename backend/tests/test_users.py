import pytest
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestUserList:
    def test_list_users(self, auth_client):
        UserFactory.create_batch(3)
        response = auth_client.get("/api/users/")
        assert response.status_code == 200
        # auth_client creates 1 user + 3 = 4 total
        assert len(response.data) == 4

    def test_list_users_unauthenticated(self, api_client):
        response = api_client.get("/api/users/")
        assert response.status_code == 401


class TestUserDetail:
    def test_get_user_detail(self, auth_client):
        user = UserFactory(name="李四", github_id="lisi")
        response = auth_client.get(f"/api/users/{user.id}/")
        assert response.status_code == 200
        assert response.data["name"] == "李四"
        assert response.data["github_id"] == "lisi"
