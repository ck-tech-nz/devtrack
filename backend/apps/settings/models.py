from django.db import models
from solo.models import SingletonModel


def default_labels():
    return ["前端", "后端", "Bug", "优化", "需求", "文档", "CI/CD", "安全", "性能", "UI/UX"]


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
