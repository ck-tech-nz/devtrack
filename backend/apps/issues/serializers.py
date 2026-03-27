import re
from rest_framework import serializers
from django.utils import timezone
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from apps.settings.models import SiteSettings
from apps.repos.serializers import GitHubIssueBriefSerializer
from apps.tools.serializers import AttachmentSerializer
from .models import Issue, Activity

User = get_user_model()


def _sync_attachments(issue, user):
    """Link Attachment records whose URL appears in issue.description to the issue."""
    from apps.tools.models import Attachment
    if not issue.description:
        return
    minio_base = django_settings.MINIO_PUBLIC_URL
    urls = set(re.findall(r'https?://\S+', issue.description))
    cleaned = {re.sub(r'[)"\']+$', '', u) for u in urls}
    for url in cleaned:
        if url.startswith(minio_base):
            for att in Attachment.objects.filter(file_url=url, uploaded_by=user):
                issue.attachments.add(att)


class ActivitySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    issue_title = serializers.CharField(source="issue.title", read_only=True)
    issue_id = serializers.IntegerField(source="issue.id", read_only=True)

    class Meta:
        model = Activity
        fields = ["id", "user_name", "action", "issue_title", "issue_id", "detail", "created_at"]


class GitHubIssueLinkSerializer(serializers.ModelSerializer):
    """列表页用的轻量序列化，只返回构建链接需要的字段。"""
    repo_full_name = serializers.CharField(source="repo.full_name", read_only=True)

    class Meta:
        from apps.repos.models import GitHubIssue
        model = GitHubIssue
        fields = ["id", "github_id", "repo_full_name", "title", "state"]
        read_only_fields = fields


class IssueListSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source="reporter.name", read_only=True, default=None)
    assignee_name = serializers.CharField(source="assignee.name", read_only=True, default=None)
    helpers = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    helpers_names = serializers.SerializerMethodField()
    resolution_hours = serializers.SerializerMethodField()
    github_issues = GitHubIssueLinkSerializer(many=True, read_only=True)

    class Meta:
        model = Issue
        fields = [
            "id", "project", "repo", "title", "priority",
            "status", "labels", "reporter", "reporter_name",
            "assignee", "assignee_name", "helpers", "helpers_names", "remark", "cause", "solution",
            "resolution_hours", "created_at", "updated_at", "github_issues",
        ]

    def get_helpers_names(self, obj):
        return [u.name or u.username for u in obj.helpers.all()]

    def get_resolution_hours(self, obj):
        if obj.resolved_at and obj.created_at:
            delta = obj.resolved_at - obj.created_at
            return round(delta.total_seconds() / 3600, 1)
        return None


class IssueDetailSerializer(IssueListSerializer):
    github_issues = GitHubIssueBriefSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta(IssueListSerializer.Meta):
        fields = IssueListSerializer.Meta.fields + [
            "description", "estimated_completion",
            "actual_hours", "resolved_at", "github_issues", "attachments",
        ]


class IssueCreateUpdateSerializer(serializers.ModelSerializer):
    helpers = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), required=False,
    )

    class Meta:
        model = Issue
        fields = [
            "id", "project", "repo", "title", "description", "priority", "status",
            "labels", "assignee", "helpers", "remark", "estimated_completion",
            "actual_hours", "cause", "solution",
        ]
        read_only_fields = ["id"]

    def validate_labels(self, value):
        site_settings = SiteSettings.get_solo()
        valid = set(site_settings.labels)
        invalid = [l for l in value if l not in valid]
        if invalid:
            raise serializers.ValidationError(f"无效的标签: {invalid}")
        return value

    def validate_priority(self, value):
        site_settings = SiteSettings.get_solo()
        if value not in site_settings.priorities:
            raise serializers.ValidationError(f"无效的优先级: {value}")
        return value

    def validate_status(self, value):
        site_settings = SiteSettings.get_solo()
        if value not in site_settings.issue_statuses:
            raise serializers.ValidationError(f"无效的状态: {value}")
        return value

    def create(self, validated_data):
        helpers = validated_data.pop("helpers", [])
        validated_data["reporter"] = self.context["request"].user
        issue = super().create(validated_data)
        if helpers:
            issue.helpers.set(helpers)
        Activity.objects.create(
            user=self.context["request"].user,
            issue=issue,
            action="created",
        )
        _sync_attachments(issue, self.context["request"].user)
        return issue

    def update(self, instance, validated_data):
        helpers = validated_data.pop("helpers", None)
        user = self.context["request"].user
        old_status = instance.status
        old_assignee = instance.assignee_id
        issue = super().update(instance, validated_data)
        if helpers is not None:
            issue.helpers.set(helpers)

        new_status = validated_data.get("status")
        if new_status and new_status != old_status:
            action = "resolved" if new_status == "已解决" else "closed" if new_status == "已关闭" else "updated"
            Activity.objects.create(
                user=user, issue=issue, action=action,
                detail=f"状态从 {old_status} 改为 {new_status}",
            )
            if new_status == "已解决" and not issue.resolved_at:
                issue.resolved_at = timezone.now()
                issue.save(update_fields=["resolved_at"])

        new_assignee = validated_data.get("assignee")
        if "assignee" in validated_data and str(getattr(new_assignee, "id", None)) != str(old_assignee):
            Activity.objects.create(
                user=user, issue=issue, action="assigned",
                detail=f"分配给 {new_assignee.name}" if new_assignee else "取消分配",
            )

        _sync_attachments(issue, user)
        return issue


class BatchUpdateSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField())
    action = serializers.ChoiceField(choices=["assign", "set_priority"])
    value = serializers.CharField()
