from django.contrib import admin
from .models import Repo


@admin.register(Repo)
class RepoAdmin(admin.ModelAdmin):
    list_display = ("full_name", "language", "stars", "status", "connected_at")
