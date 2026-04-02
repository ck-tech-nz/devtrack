from rest_framework import serializers
from .models import Notification, NotificationRecipient


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.BooleanField(source="recipient.is_read", read_only=True)
    read_at = serializers.DateTimeField(source="recipient.read_at", read_only=True)
    source_user_name = serializers.CharField(source="source_user.name", read_only=True, default=None)
    source_issue_title = serializers.CharField(source="source_issue.title", read_only=True, default=None)
    source_issue_id = serializers.UUIDField(read_only=True, default=None)

    class Meta:
        model = Notification
        fields = [
            "id", "notification_type", "title", "content",
            "source_user_name", "source_issue_id", "source_issue_title",
            "is_read", "read_at", "created_at",
        ]
