from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Issue, Activity


@admin.register(Issue)
class IssueAdmin(ModelAdmin):
    list_display = ("id", "title", "priority", "status", "assignee", "created_by", "is_deleted", "created_at")
    list_filter = ("priority", "status", "is_deleted")
    search_fields = ("title",)

    def get_queryset(self, request):
        return Issue.all_objects.all()


@admin.register(Activity)
class ActivityAdmin(ModelAdmin):
    list_display = ("issue", "user", "action", "created_at")
    list_filter = ("action",)
