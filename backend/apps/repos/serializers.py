from rest_framework import serializers
from .models import Repo, GitHubIssue


class GitHubIssueBriefSerializer(serializers.ModelSerializer):
    repo_full_name = serializers.CharField(source="repo.full_name", read_only=True)

    class Meta:
        model = GitHubIssue
        fields = [
            "id", "repo", "repo_full_name", "github_id", "title",
            "state", "labels", "assignees",
            "github_created_at", "github_updated_at",
        ]
        read_only_fields = fields


class GitHubIssueDetailSerializer(serializers.ModelSerializer):
    repo_full_name = serializers.CharField(source="repo.full_name", read_only=True)
    repo_name = serializers.CharField(source="repo.name", read_only=True)

    class Meta:
        model = GitHubIssue
        fields = [
            "id", "repo", "repo_full_name", "repo_name", "github_id", "title", "body",
            "state", "labels", "assignees",
            "github_created_at", "github_updated_at", "github_closed_at", "synced_at",
        ]
        read_only_fields = fields


class RepoSerializer(serializers.ModelSerializer):
    open_issues_count = serializers.IntegerField(read_only=True, default=0)
    closed_issues_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Repo
        # github_token 故意不包含在内，防止凭据泄露
        fields = [
            "id", "name", "full_name", "url", "description",
            "default_branch", "language", "stars", "status",
            "connected_at", "last_synced_at",
            "open_issues_count", "closed_issues_count",
        ]
        read_only_fields = ["id", "connected_at", "last_synced_at"]
