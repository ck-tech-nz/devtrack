from django.contrib import admin
from solo.admin import SingletonModelAdmin
from unfold.admin import ModelAdmin
from .models import DatabaseBackup, SiteSettings
from .widgets import JsonReadonlyToggleWidget


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin, SingletonModelAdmin):
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ("labels", "priorities", "issue_statuses"):
            kwargs["widget"] = JsonReadonlyToggleWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(DatabaseBackup)
class DatabaseBackupAdmin(ModelAdmin):
    list_display = ("filename", "status", "file_size", "created_by", "created_at")
    list_filter = ("status",)
    readonly_fields = ("filename", "file_size", "status", "error_message", "created_by", "created_at")
