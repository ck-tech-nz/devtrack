import pytest
from django.contrib.auth.models import Group, Permission
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestPermissionEnforcement:
    def test_readonly_user_cannot_create_project(self, api_client):
        group = Group.objects.create(name="只读成员")
        view_perm = Permission.objects.get(codename="view_project")
        group.permissions.add(view_perm)
        user = UserFactory()
        user.groups.add(group)
        api_client.force_authenticate(user=user)
        response = api_client.post("/api/projects/", {"name": "Test", "status": "进行中"})
        assert response.status_code == 403

    def test_readonly_user_can_list_projects(self, api_client):
        group = Group.objects.create(name="只读成员")
        view_perm = Permission.objects.get(codename="view_project")
        group.permissions.add(view_perm)
        user = UserFactory()
        user.groups.add(group)
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/projects/")
        assert response.status_code == 200

    def test_no_view_permission_cannot_list_projects(self, api_client):
        """User with NO view_project permission should get 403 on GET."""
        group = Group.objects.create(name="空权限组")
        user = UserFactory()
        user.groups.add(group)
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/projects/")
        assert response.status_code == 403

    def test_admin_can_create_project(self, api_client):
        group = Group.objects.create(name="管理员测试")
        for perm in Permission.objects.filter(content_type__app_label__in=["projects", "issues"]):
            group.permissions.add(perm)
        user = UserFactory()
        user.groups.add(group)
        api_client.force_authenticate(user=user)
        response = api_client.post("/api/projects/", {"name": "Test", "status": "进行中"})
        assert response.status_code == 201

    def test_me_returns_permissions(self, api_client):
        group = Group.objects.create(name="开发者")
        perm = Permission.objects.get(codename="view_project")
        group.permissions.add(perm)
        user = UserFactory()
        user.groups.add(group)
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/auth/me/")
        assert "projects.view_project" in response.data["permissions"]
