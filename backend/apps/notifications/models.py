import uuid
from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        MENTION = "mention", "提及"
        SYSTEM = "system", "系统"
        BROADCAST = "broadcast", "广播"

    class TargetType(models.TextChoices):
        USER = "user", "个人"
        GROUP = "group", "组"
        ALL = "all", "全员"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_type = models.CharField(max_length=20, choices=Type.choices, verbose_name="类型")
    title = models.CharField(max_length=200, verbose_name="标题")
    content = models.TextField(blank=True, verbose_name="内容")
    source_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sent_notifications", verbose_name="触发者",
    )
    source_issue = models.ForeignKey(
        "issues.Issue", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="notifications", verbose_name="关联问题",
    )
    target_type = models.CharField(max_length=10, choices=TargetType.choices, verbose_name="目标类型")
    target_group = models.ForeignKey(
        "auth.Group", on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="目标组",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "通知"
        verbose_name_plural = "通知"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class NotificationRecipient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="recipients",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="notification_recipients",
    )
    is_read = models.BooleanField(default=False, verbose_name="已读")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="阅读时间")
    is_deleted = models.BooleanField(default=False, verbose_name="已删除")

    class Meta:
        verbose_name = "通知接收"
        verbose_name_plural = "通知接收"
        unique_together = [("notification", "user")]

    def __str__(self):
        return f"{self.notification.title} → {self.user}"
