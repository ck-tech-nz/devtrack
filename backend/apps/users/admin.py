from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from apps.widgets import JsonSchemaWidget
from .models import User

USER_SETTINGS_SCHEMA = {
    "sidebar_auto_collapse": {"type": "boolean", "label": "侧边栏自动折叠", "default": False},
    "issues_view_mode": {"type": "select", "label": "问题视图模式", "choices": ["kanban", "table"], "default": "table"},
    "project_view_mode": {"type": "select", "label": "项目视图模式", "choices": ["kanban", "table"], "default": "kanban"},
    "theme": {"type": "select", "label": "主题", "choices": ["light", "dark", "auto"], "default": "light"},
}


@admin.register(User)
class UserAdmin(ModelAdmin, BaseUserAdmin):
    list_display = ("username", "name", "email", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (("扩展信息", {"fields": ("name", "github_id", "avatar", "settings")}),)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "settings":
            kwargs["widget"] = JsonSchemaWidget(schema=USER_SETTINGS_SCHEMA)
        return super().formfield_for_dbfield(db_field, request, **kwargs)
