import pytest
from rest_framework.test import APIClient
from tests.factories import ExternalAPIKeyFactory, UserFactory


@pytest.fixture
def api_key_obj():
    return ExternalAPIKeyFactory()


@pytest.fixture
def external_client(api_key_obj):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {api_key_obj.key}")
    return client


@pytest.mark.django_db
class TestExternalNotificationCreate:
    URL = "/api/external/notifications/create/"

    def test_create_broadcast_publishes_to_all_active_users(
        self, external_client, api_key_obj,
    ):
        UserFactory()
        UserFactory()
        UserFactory(is_active=False)  # should be skipped

        data = {
            "title": "DevTrakr 更新",
            "content": "## 新功能\n上线了 X",
            "target_type": "all",
            "is_draft": False,
        }
        resp = external_client.post(self.URL, data, format="json")

        assert resp.status_code == 201, resp.data
        assert "id" in resp.data
        # 1 (default_assignee) + 2 active users = 3
        assert resp.data["recipients"] == 3

        from apps.notifications.models import Notification
        notif = Notification.objects.get(pk=resp.data["id"])
        assert notif.title == "DevTrakr 更新"
        assert notif.is_draft is False
        assert notif.notification_type == "broadcast"
        assert notif.source_user == api_key_obj.default_assignee

    def test_create_with_is_draft_skips_recipients(self, external_client):
        UserFactory()

        data = {
            "title": "草稿",
            "content": "stub",
            "target_type": "all",
            "is_draft": True,
        }
        resp = external_client.post(self.URL, data, format="json")

        assert resp.status_code == 201
        assert resp.data["recipients"] == 0

        from apps.notifications.models import Notification
        notif = Notification.objects.get(pk=resp.data["id"])
        assert notif.is_draft is True
        assert notif.recipients.count() == 0

    def test_create_minimal_payload_requires_only_title(self, external_client):
        resp = external_client.post(self.URL, {"title": "最简"}, format="json")
        assert resp.status_code == 201

        from apps.notifications.models import Notification
        notif = Notification.objects.get(pk=resp.data["id"])
        assert notif.target_type == "all"
        assert notif.is_draft is False

    def test_missing_title_returns_400(self, external_client):
        resp = external_client.post(self.URL, {"content": "无标题"}, format="json")
        assert resp.status_code == 400

    def test_unauthenticated_returns_401(self):
        client = APIClient()
        resp = client.post(self.URL, {"title": "x"}, format="json")
        assert resp.status_code == 401

    def test_invalid_key_returns_401(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer sk-invalid")
        resp = client.post(self.URL, {"title": "x"}, format="json")
        assert resp.status_code == 401
