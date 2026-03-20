import uuid
from django.db import models


class Repo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="仓库名")
    full_name = models.CharField(max_length=200, verbose_name="完整名称")
    url = models.CharField(max_length=500, verbose_name="GitHub URL")
    description = models.TextField(blank=True, verbose_name="描述")
    default_branch = models.CharField(max_length=50, default="main", verbose_name="默认分支")
    language = models.CharField(max_length=50, blank=True, verbose_name="主要语言")
    stars = models.PositiveIntegerField(default=0, verbose_name="Star 数")
    status = models.CharField(max_length=20, default="在线", verbose_name="状态")
    connected_at = models.DateTimeField(auto_now_add=True, verbose_name="绑定时间")

    class Meta:
        verbose_name = "GitHub 仓库"
        verbose_name_plural = "GitHub 仓库"
        ordering = ["-connected_at"]

    def __str__(self):
        return self.full_name
