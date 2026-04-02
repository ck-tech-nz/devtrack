import pytest
from tests.factories import (
    UserFactory, IssueFactory, NotificationFactory, NotificationRecipientFactory,
)

pytestmark = pytest.mark.django_db


class TestNotificationList:
    def test_list_own_notifications(self, auth_client, auth_user):
        n = NotificationFactory()
        NotificationRecipientFactory(notification=n, user=auth_user)
        # Another user's notification — should not appear
        NotificationRecipientFactory()
        response = auth_client.get("/api/notifications/")
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["title"] == n.title

    def test_filter_unread(self, auth_client, auth_user):
        n1 = NotificationFactory(title="unread")
        NotificationRecipientFactory(notification=n1, user=auth_user, is_read=False)
        n2 = NotificationFactory(title="read")
        NotificationRecipientFactory(notification=n2, user=auth_user, is_read=True)
        response = auth_client.get("/api/notifications/?is_read=false")
        assert response.data["count"] == 1
        assert response.data["results"][0]["title"] == "unread"

    def test_deleted_not_shown(self, auth_client, auth_user):
        n = NotificationFactory()
        NotificationRecipientFactory(notification=n, user=auth_user, is_deleted=True)
        response = auth_client.get("/api/notifications/")
        assert response.data["count"] == 0

    def test_unauthenticated(self, api_client):
        response = api_client.get("/api/notifications/")
        assert response.status_code == 401


class TestUnreadCount:
    def test_count(self, auth_client, auth_user):
        for _ in range(3):
            n = NotificationFactory()
            NotificationRecipientFactory(notification=n, user=auth_user, is_read=False)
        n_read = NotificationFactory()
        NotificationRecipientFactory(notification=n_read, user=auth_user, is_read=True)
        response = auth_client.get("/api/notifications/unread-count/")
        assert response.status_code == 200
        assert response.data["count"] == 3


class TestMarkRead:
    def test_mark_single_read(self, auth_client, auth_user):
        n = NotificationFactory()
        NotificationRecipientFactory(notification=n, user=auth_user, is_read=False)
        response = auth_client.post(f"/api/notifications/{n.id}/read/")
        assert response.status_code == 200
        assert response.data["detail"] == "已标记已读"
        # Verify via unread count
        response = auth_client.get("/api/notifications/unread-count/")
        assert response.data["count"] == 0

    def test_mark_nonexistent(self, auth_client):
        import uuid
        response = auth_client.post(f"/api/notifications/{uuid.uuid4()}/read/")
        assert response.status_code == 404


class TestMarkAllRead:
    def test_mark_all(self, auth_client, auth_user):
        for _ in range(3):
            n = NotificationFactory()
            NotificationRecipientFactory(notification=n, user=auth_user, is_read=False)
        response = auth_client.post("/api/notifications/read-all/")
        assert response.status_code == 200
        assert response.data["updated"] == 3
        response = auth_client.get("/api/notifications/unread-count/")
        assert response.data["count"] == 0


class TestDeleteNotification:
    def test_soft_delete(self, auth_client, auth_user):
        n = NotificationFactory()
        NotificationRecipientFactory(notification=n, user=auth_user)
        response = auth_client.delete(f"/api/notifications/{n.id}/")
        assert response.status_code == 204
        # Should not appear in list
        response = auth_client.get("/api/notifications/")
        assert response.data["count"] == 0


class TestBroadcastAdmin:
    def test_broadcast_creates_recipients(self, auth_user):
        """Verify the admin save_model hook creates recipients for all active users."""
        from apps.notifications.models import Notification, NotificationRecipient
        n = Notification.objects.create(
            notification_type="broadcast",
            title="系统公告",
            content="维护通知",
            target_type="all",
        )
        # Simulate what admin does
        from apps.notifications.admin import NotificationAdmin
        admin_instance = NotificationAdmin(Notification, None)
        admin_instance._create_recipients(n)
        assert NotificationRecipient.objects.filter(notification=n, user=auth_user).exists()


class TestMentionParsing:
    def test_extract_mentions(self):
        from apps.notifications.services import extract_mentioned_user_ids
        text = "请 @[张三](user:5) 和 @[李四](user:12) 看看这个问题"
        ids = extract_mentioned_user_ids(text)
        assert ids == {5, 12}

    def test_extract_no_mentions(self):
        from apps.notifications.services import extract_mentioned_user_ids
        assert extract_mentioned_user_ids("普通文本") == set()

    def test_extract_ignores_invalid(self):
        from apps.notifications.services import extract_mentioned_user_ids
        text = "邮件 user@example.com 和 @[张三](user:5)"
        assert extract_mentioned_user_ids(text) == {5}

    def test_create_mention_notifications(self, auth_user):
        from apps.notifications.services import create_mention_notifications
        from apps.notifications.models import NotificationRecipient
        user2 = UserFactory()
        issue = IssueFactory(reporter=auth_user)
        new_desc = f"请 @[{user2.name}](user:{user2.id}) 看看"
        create_mention_notifications(
            issue=issue,
            old_description="",
            new_description=new_desc,
            actor=auth_user,
        )
        assert NotificationRecipient.objects.filter(user=user2).count() == 1
        notif = NotificationRecipient.objects.get(user=user2).notification
        assert notif.notification_type == "mention"
        assert notif.source_issue == issue
        assert notif.source_user == auth_user

    def test_no_self_notification(self, auth_user):
        from apps.notifications.services import create_mention_notifications
        from apps.notifications.models import NotificationRecipient
        issue = IssueFactory(reporter=auth_user)
        new_desc = f"@[{auth_user.name}](user:{auth_user.id}) 看看"
        create_mention_notifications(
            issue=issue,
            old_description="",
            new_description=new_desc,
            actor=auth_user,
        )
        assert NotificationRecipient.objects.filter(user=auth_user).count() == 0

    def test_no_duplicate_on_update(self, auth_user):
        from apps.notifications.services import create_mention_notifications
        from apps.notifications.models import NotificationRecipient
        user2 = UserFactory()
        issue = IssueFactory(reporter=auth_user)
        desc = f"@[{user2.name}](user:{user2.id}) 看看"
        create_mention_notifications(issue=issue, old_description="", new_description=desc, actor=auth_user)
        create_mention_notifications(issue=issue, old_description=desc, new_description=desc, actor=auth_user)
        assert NotificationRecipient.objects.filter(user=user2).count() == 1
