from django.conf import settings as django_settings
from django.db import models
from solo.models import SingletonModel


def default_labels():
    return {
        "前端": {"foreground": "#ffffff", "background": "#0075ca", "description": "前端相关问题"},
        "后端": {"foreground": "#ffffff", "background": "#e99695", "description": "后端相关问题"},
        "Bug": {"foreground": "#ffffff", "background": "#d73a4a", "description": "程序错误"},
        "优化": {"foreground": "#ffffff", "background": "#a2eeef", "description": "性能或代码优化"},
        "需求": {"foreground": "#ffffff", "background": "#7057ff", "description": "新功能需求"},
        "文档": {"foreground": "#ffffff", "background": "#0075ca", "description": "文档改进"},
        "CI/CD": {"foreground": "#ffffff", "background": "#e4e669", "description": "持续集成与部署"},
        "安全": {"foreground": "#ffffff", "background": "#d73a4a", "description": "安全相关问题"},
        "性能": {"foreground": "#ffffff", "background": "#f9d0c4", "description": "性能问题"},
        "UI/UX": {"foreground": "#ffffff", "background": "#bfd4f2", "description": "界面与体验"},
    }


def default_priorities():
    return ["P0", "P1", "P2", "P3"]


def default_issue_statuses():
    return ["待处理", "进行中", "已解决", "已关闭"]


class SiteSettings(SingletonModel):
    labels = models.JSONField(
        default=default_labels,
        verbose_name="Issue 标签",
    )
    priorities = models.JSONField(
        default=default_priorities,
        verbose_name="优先级选项",
    )
    issue_statuses = models.JSONField(
        default=default_issue_statuses,
        verbose_name="Issue 状态选项",
    )

    class Meta:
        verbose_name = "系统设置"
        verbose_name_plural = "系统设置"

    def __str__(self):
        return "系统设置"


class DatabaseBackup(models.Model):
    filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("running", "备份中"),
            ("success", "成功"),
            ("failed", "失败"),
        ],
    )
    error_message = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "数据库备份"
        verbose_name_plural = "数据库备份"

    def __str__(self):
        return self.filename
