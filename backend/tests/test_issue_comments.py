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
