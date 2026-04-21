from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import KPISnapshot


@admin.register(KPISnapshot)
class KPISnapshotAdmin(ModelAdmin):
    list_display = ("user", "period_start", "period_end", "computed_at")
    list_filter = ("period_start", "period_end")
    search_fields = ("user__username", "user__name")
    readonly_fields = ("id", "computed_at", "created_at")
