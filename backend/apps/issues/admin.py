from django.contrib import admin
from .models import Issue, Activity


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "priority", "status", "assignee", "created_at")
    list_filter = ("priority", "status")
    search_fields = ("title",)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("issue", "user", "action", "created_at")
    list_filter = ("action",)
