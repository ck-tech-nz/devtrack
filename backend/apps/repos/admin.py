from django.contrib import admin
from .models import Repo, GitHubIssue


@admin.register(Repo)
class RepoAdmin(admin.ModelAdmin):
    list_display = ("full_name", "language", "stars", "status", "last_synced_at", "connected_at")
    readonly_fields = ("connected_at", "last_synced_at")


@admin.register(GitHubIssue)
class GitHubIssueAdmin(admin.ModelAdmin):
    list_display = ("repo", "github_id", "title", "state", "synced_at")
    readonly_fields = (
        "repo", "github_id", "title", "body", "state", "labels",
        "assignees", "github_created_at", "github_updated_at",
        "github_closed_at", "synced_at",
    )
    list_filter = ("state", "repo")
    search_fields = ("title",)
