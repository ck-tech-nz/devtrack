import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from page_perms.models import PageRoute

pytestmark = pytest.mark.django_db


class TestPermissionList:
    def test_superuser_can_list(self, superuser_client):
        response = superuser_client.get("/api/page-perms/permissions/")
        assert response.status_code == 200
        assert len(response.data) > 0

    def test_regular_user_cannot_list(self, regular_client):
        response = regular_client.get("/api/page-perms/permissions/")
        assert response.status_code == 403

    def test_permissions_have_source_field(self, superuser_client):
        response = superuser_client.get("/api/page-perms/permissions/")
        sources = {p["source"] for p in response.data}
        assert "model" in sources


class TestPermissionCreate:
    def test_create_custom_permission(self, superuser_client):
        response = superuser_client.post("/api/page-perms/permissions/", {
            "codename": "view_analytics",
            "name": "Can view analytics",
        }, format="json")
        assert response.status_code == 201
        assert response.data["source"] == "custom"
        assert response.data["app_label"] == "page_perms"

    def test_duplicate_codename_returns_400(self, superuser_client):
        ct = ContentType.objects.get_for_model(PageRoute)
        Permission.objects.create(content_type=ct, codename="existing", name="Existing")
        response = superuser_client.post("/api/page-perms/permissions/", {
            "codename": "existing",
            "name": "Duplicate",
        }, format="json")
        assert response.status_code == 400


class TestPermissionDelete:
    def test_delete_custom_permission(self, superuser_client):
        ct = ContentType.objects.get_for_model(PageRoute)
        perm = Permission.objects.create(content_type=ct, codename="temp", name="Temp")
        response = superuser_client.delete(f"/api/page-perms/permissions/{perm.pk}/")
        assert response.status_code == 204

    def test_cannot_delete_model_permission(self, superuser_client):
        perm = Permission.objects.get(codename="view_issue")
        response = superuser_client.delete(f"/api/page-perms/permissions/{perm.pk}/")
        assert response.status_code == 400
        assert "model-generated" in response.data["detail"]
