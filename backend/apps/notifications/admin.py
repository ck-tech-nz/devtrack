from django.contrib import admin
from django.contrib.auth import get_user_model
from unfold.admin import ModelAdmin, TabularInline
from .models import Notification, NotificationRecipient

User = get_user_model()


class RecipientInline(TabularInline):
    model = NotificationRecipient
    extra = 0
    readonly_fields = ("user", "is_read", "read_at")


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ("title", "notification_type", "target_type", "created_at")
    list_filter = ("notification_type", "target_type")
    search_fields = ("title",)
    inlines = [RecipientInline]

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


@admin.register(NotificationRecipient)
class NotificationRecipientAdmin(ModelAdmin):
    list_display = ("notification", "user", "is_read", "is_deleted")
    list_filter = ("is_read", "is_deleted")
