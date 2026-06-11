import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.issues.models import IssueComment
from tests.factories import IssueCommentFactory, IssueFactory, UserFactory

pytestmark = pytest.mark.django_db


# ---------- 本文件公用夹具 ----------

@pytest.fixture
def author():
    return UserFactory()


@pytest.fixture
def author_client(author):
    client = APIClient()
    client.force_authenticate(user=author)
    return client


@pytest.fixture
def other_client():
    client = APIClient()
    client.force_authenticate(user=UserFactory())
    return client


@pytest.fixture
def admin_client():
    user = UserFactory()
    group, _ = Group.objects.get_or_create(name="管理员")
    user.groups.add(group)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def issue():
    return IssueFactory()


def mention(user) -> str:
    """构造一条 @提及 文本，格式同前端 MentionDropdown 插入的格式。"""
    return f"@[{user.name or user.username}](user:{user.id})"


class TestIssueCommentModel:
    def test_ordering_oldest_first(self, issue, author):
        from datetime import timedelta
        from django.utils import timezone
        c1 = IssueCommentFactory(issue=issue, author=author)
        c2 = IssueCommentFactory(issue=issue, author=author)
        # 把 c2 回拨到 c1 之前,验证排序确实按 created_at 而非插入顺序
        IssueComment.objects.filter(pk=c2.pk).update(
            created_at=timezone.now() - timedelta(minutes=5),
        )
        assert list(issue.comments.all()) == [c2, c1]

    def test_str(self, issue, author):
        c = IssueCommentFactory(issue=issue, author=author, content="x" * 100)
        assert str(c).startswith(f"#{issue.pk} ")


class TestCommentMentionService:
    def _call(self, comment, old_content, actor):
        from apps.notifications.services import create_comment_mention_notifications
        create_comment_mention_notifications(
            comment=comment, old_content=old_content,
            new_content=comment.content, actor=actor,
        )

    def test_notifies_newly_mentioned_user(self, issue, author):
        from apps.notifications.models import Notification
        target = UserFactory()
        comment = IssueCommentFactory(
            issue=issue, author=author, content=f"请看 {mention(target)}",
        )
        self._call(comment, old_content="", actor=author)

        n = Notification.objects.filter(
            notification_type=Notification.Type.MENTION, source_issue=issue,
        ).first()
        assert n is not None
        assert f"#{issue.pk} 的评论中提到了你" in n.title
        assert n.source_user == author
        assert n.recipients.filter(user=target).exists()
        assert Notification.objects.count() == 1

    def test_self_mention_not_notified(self, issue, author):
        from apps.notifications.models import Notification
        comment = IssueCommentFactory(
            issue=issue, author=author, content=f"自言自语 {mention(author)}",
        )
        self._call(comment, old_content="", actor=author)
        assert Notification.objects.count() == 0

    def test_already_mentioned_in_old_content_not_renotified(self, issue, author):
        from apps.notifications.models import Notification
        target = UserFactory()
        comment = IssueCommentFactory(
            issue=issue, author=author, content=f"再次 {mention(target)}",
        )
        self._call(comment, old_content=f"之前 {mention(target)}", actor=author)
        assert Notification.objects.count() == 0

    def test_inactive_user_not_notified(self, issue, author):
        from apps.notifications.models import Notification
        target = UserFactory(is_active=False)
        comment = IssueCommentFactory(
            issue=issue, author=author, content=mention(target),
        )
        self._call(comment, old_content="", actor=author)
        assert Notification.objects.count() == 0

    def test_multiple_mentions_notify_each_user_once(self, issue, author):
        from apps.notifications.models import Notification
        a, b = UserFactory(), UserFactory()
        comment = IssueCommentFactory(
            issue=issue, author=author,
            content=f"{mention(a)} 和 {mention(b)} 请跟进",
        )
        self._call(comment, old_content="", actor=author)
        assert Notification.objects.count() == 2
        for target in (a, b):
            n = Notification.objects.filter(recipients__user=target).first()
            assert n is not None
            assert n.recipients.count() == 1


class TestCommentListCreate:
    def test_create_returns_201_with_payload(self, author_client, author, issue):
        resp = author_client.post(
            f"/api/issues/{issue.pk}/comments/", {"content": "第一条评论"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "第一条评论"
        assert data["author"] == author.id
        assert data["author_name"] == (author.name or author.username)
        assert data["is_edited"] is False

    def test_list_returns_oldest_first(self, author_client, issue, author):
        c1 = IssueCommentFactory(issue=issue, author=author, content="老评论")
        c2 = IssueCommentFactory(issue=issue, author=author, content="新评论")
        resp = author_client.get(f"/api/issues/{issue.pk}/comments/")
        assert resp.status_code == 200
        assert [c["id"] for c in resp.json()] == [c1.id, c2.id]

    def test_blank_content_rejected(self, author_client, issue):
        resp = author_client.post(f"/api/issues/{issue.pk}/comments/", {"content": "   "})
        assert resp.status_code == 400

    def test_overlong_content_rejected(self, author_client, issue):
        resp = author_client.post(
            f"/api/issues/{issue.pk}/comments/", {"content": "x" * 65537},
        )
        assert resp.status_code == 400

    def test_unauthenticated_401(self, api_client, issue):
        assert api_client.get(f"/api/issues/{issue.pk}/comments/").status_code == 401
        assert api_client.post(
            f"/api/issues/{issue.pk}/comments/", {"content": "x"},
        ).status_code == 401

    def test_unknown_issue_404(self, author_client):
        assert author_client.get("/api/issues/999999/comments/").status_code == 404
        assert author_client.post(
            "/api/issues/999999/comments/", {"content": "x"},
        ).status_code == 404

    def test_create_writes_commented_activity(self, author_client, author, issue):
        from apps.issues.models import Activity
        author_client.post(f"/api/issues/{issue.pk}/comments/", {"content": "评论"})
        assert Activity.objects.filter(
            issue=issue, user=author, action="commented",
        ).exists()

    def test_create_bumps_updated_at_without_history_row(self, author_client, issue):
        old_updated = issue.updated_at
        old_history = issue.history.count()
        resp = author_client.post(f"/api/issues/{issue.pk}/comments/", {"content": "bump"})
        assert resp.status_code == 201
        issue.refresh_from_db()
        assert issue.updated_at > old_updated
        # 用 queryset.update 绕过 save() → 不允许产生 simple_history 快照
        assert issue.history.count() == old_history

    def test_create_with_mention_notifies(self, author_client, issue):
        from apps.notifications.models import Notification
        target = UserFactory()
        resp = author_client.post(
            f"/api/issues/{issue.pk}/comments/",
            {"content": f"请处理 {mention(target)}"},
        )
        assert resp.status_code == 201
        n = Notification.objects.filter(
            notification_type=Notification.Type.MENTION, source_issue=issue,
        ).first()
        assert n is not None and n.recipients.filter(user=target).exists()
