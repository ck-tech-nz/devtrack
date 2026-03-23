import pytest

from page_perms.models import PageRoute
pytestmark = pytest.mark.django_db


class TestLockoutProtection:
    def test_cannot_delete_protected_route(self, superuser_client):
        route = PageRoute.objects.create(
            path="/app/permissions", label="权限管理"
        )
        response = superuser_client.delete(f"/api/page-perms/routes/{route.pk}/")
        assert response.status_code == 400
        assert "protected" in response.data["detail"].lower()

    def test_cannot_deactivate_protected_route(self, superuser_client):
        route = PageRoute.objects.create(
            path="/app/permissions", label="权限管理", is_active=True
        )
        response = superuser_client.patch(
            f"/api/page-perms/routes/{route.pk}/",
            {"is_active": False},
            format="json",
        )
        assert response.status_code == 400

    def test_can_update_other_fields_on_protected_route(self, superuser_client):
        route = PageRoute.objects.create(
            path="/app/permissions", label="权限管理"
        )
        response = superuser_client.patch(
            f"/api/page-perms/routes/{route.pk}/",
            {"label": "Permission Management"},
            format="json",
        )
        assert response.status_code == 200
