from django.contrib import admin
from .models import PageRoute

try:
    from unfold.admin import ModelAdmin as BaseModelAdmin
except ImportError:
    BaseModelAdmin = admin.ModelAdmin


@admin.register(PageRoute)
class PageRouteAdmin(BaseModelAdmin):
    list_display = ("path", "label", "permission", "show_in_nav", "is_active", "sort_order", "source")
    list_filter = ("is_active", "show_in_nav", "source")
    search_fields = ("path", "label")
