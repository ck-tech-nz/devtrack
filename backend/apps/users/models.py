import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, verbose_name="姓名")
    github_id = models.CharField(max_length=100, blank=True, verbose_name="GitHub ID")
    avatar = models.URLField(blank=True, verbose_name="头像")

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return self.name or self.username
