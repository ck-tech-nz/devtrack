from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect
from django.urls import reverse
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action
from .models import Notification, NotificationRecipient
from .services import RemotePublishError, publish_notification_to_remote

User = get_user_model()


class RecipientInline(TabularInline):
    model = NotificationRecipient
    extra = 0
    readonly_fields = ("user",  "read_at")


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ("title", "notification_type", "target_type", "is_draft", "created_at")
    list_filter = ("notification_type", "target_type", "is_draft")
    search_fields = ("title",)
    inlines = [RecipientInline]
    actions_detail = ["publish_to_test", "publish_to_prod"]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            self._create_recipients(obj)

    def _create_recipients(self, notification):
        if notification.target_type == Notification.TargetType.ALL:
            users = User.objects.filter(is_active=True)
        elif notification.target_type == Notification.TargetType.GROUP and notification.target_group:
            users = notification.target_group.user_set.filter(is_active=True)
        else:
            return
        recipients = [
            NotificationRecipient(notification=notification, user=u)
            for u in users
        ]
        NotificationRecipient.objects.bulk_create(recipients, ignore_conflicts=True)

    def _publish_to(self, request, object_id, env):
        notification = Notification.objects.get(pk=object_id)
        try:
            result = publish_notification_to_remote(notification, env=env)
        except (ImproperlyConfigured, RemotePublishError) as e:
            messages.error(request, f"发布到 {env} 失败:{e}")
        else:
            messages.success(
                request,
                f"已发布到 {env},远端 ID {result.get('id')},接收人 {result.get('recipients')}",
            )
        return HttpResponseRedirect(
            reverse("admin:notifications_notification_change", args=[object_id]),
        )

    @action(description="发布到 test")
    def publish_to_test(self, request, object_id):
        return self._publish_to(request, object_id, env="test")

    @action(description="发布到 prod")
    def publish_to_prod(self, request, object_id):
        return self._publish_to(request, object_id, env="prod")


@admin.register(NotificationRecipient)
class NotificationRecipientAdmin(ModelAdmin):
    list_display = ("notification", "user", "is_read", "is_deleted")
    list_filter = ("is_read", "is_deleted")
