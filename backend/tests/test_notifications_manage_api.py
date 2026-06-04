"""Tests for the Notification manage REST API (the endpoints the frontend calls).

The admin-action publish path is covered in test_notifications_admin_actions.py;
this file covers the DRF ManagePublishView at /api/notifications/manage/<id>/publish/,
which the Nuxt 通知管理 page hits when the user clicks 发布.
"""
import pytest

from apps.notifications.models import Notification
from tests.factories import NotificationFactory, UserFactory


@pytest.mark.django_db
class TestManagePublishAPI:
    def _url(self, notif):
        return f"/api/notifications/manage/{notif.pk}/publish/"

    def test_publish_draft_returns_200_and_generates_recipients(self, auth_client):
        # Extra active user so a target_type="all" broadcast reaches >1 person.
        UserFactory()
        notif = NotificationFactory(target_type="all", is_draft=True)
        assert notif.recipients.count() == 0

        resp = auth_client.post(self._url(notif))

        assert resp.status_code == 200, resp.content
        notif.refresh_from_db()
        assert notif.is_draft is False
        # Recipients must be materialized, otherwise the broadcast reaches nobody.
        assert notif.recipients.count() >= 2
        assert resp.data["recipients"] == notif.recipients.count()

    def test_publish_already_published_returns_400(self, auth_client):
        notif = NotificationFactory(target_type="all", is_draft=False)

        resp = auth_client.post(self._url(notif))

        assert resp.status_code == 400

    def test_publish_missing_returns_404(self, auth_client):
        import uuid
        resp = auth_client.post(f"/api/notifications/manage/{uuid.uuid4()}/publish/")
        assert resp.status_code == 404
