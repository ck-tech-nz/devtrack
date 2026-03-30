from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Attachment


@admin.register(Attachment)
class AttachmentAdmin(ModelAdmin):
    list_display = ["file_name", "mime_type", "file_size_kb", "uploaded_by", "created_at"]
    list_filter = ["mime_type", "created_at"]
    search_fields = ["file_name", "uploaded_by__name"]
    raw_id_fields = ["uploaded_by"]
    readonly_fields = ["id", "file_key", "file_url", "file_size", "mime_type", "created_at"]

    @admin.display(description="大小 (KB)")
    def file_size_kb(self, obj):
        return f"{obj.file_size // 1024} KB"
