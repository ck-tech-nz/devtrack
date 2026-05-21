import pytest
from django.core.exceptions import ValidationError

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


class TestHierarchyDepthGuard:
    def test_parent_cannot_have_parent(self):
        a = PageRoute.objects.create(path="#group:a", label="A", is_group=True)
        b = PageRoute.objects.create(path="#group:b", label="B", is_group=True, parent=a)
        # b 已挂在 a 下面 —— 不允许再当某个 c 的 parent
        c = PageRoute(path="/app/c", label="C", parent=b)
        with pytest.raises(ValidationError):
            c.full_clean()

    def test_leaf_cannot_become_parent(self):
        leaf = PageRoute.objects.create(path="/app/leaf", label="Leaf")
        # 叶子不能当父
        c = PageRoute(path="/app/c", label="C", parent=leaf)
        with pytest.raises(ValidationError):
            c.full_clean()

    def test_route_cannot_be_its_own_parent(self):
        g = PageRoute.objects.create(path="#group:g", label="G", is_group=True)
        g.parent = g
        with pytest.raises(ValidationError):
            g.full_clean()
