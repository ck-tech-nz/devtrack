import re
from django.contrib.auth import get_user_model
from .models import Notification, NotificationRecipient

User = get_user_model()

MENTION_RE = re.compile(r'@\[([^\]]+)\]\(user:(\d+)\)')


def extract_mentioned_user_ids(text: str) -> set[int]:
    return {int(m.group(2)) for m in MENTION_RE.finditer(text)}


def create_mention_notifications(*, issue, old_description: str, new_description: str, actor):
    old_ids = extract_mentioned_user_ids(old_description)
    new_ids = extract_mentioned_user_ids(new_description)
    added_ids = new_ids - old_ids - {actor.id}

    if not added_ids:
        return

    users = User.objects.filter(id__in=added_ids, is_active=True)
    for user in users:
        notification = Notification.objects.create(
            notification_type=Notification.Type.MENTION,
            title=f"{actor.name or actor.username} 在 #{issue.pk} 中提到了你",
            content=f"问题: {issue.title}",
            source_user=actor,
            source_issue=issue,
            target_type=Notification.TargetType.USER,
        )
        NotificationRecipient.objects.create(
            notification=notification,
            user=user,
        )
