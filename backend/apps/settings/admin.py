from django.contrib import admin
from solo.admin import SingletonModelAdmin
from unfold.admin import ModelAdmin
from .models import SiteSettings
from .widgets import JsonReadonlyToggleWidget


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin, SingletonModelAdmin):
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ("labels", "priorities", "issue_statuses"):
            kwargs["widget"] = JsonReadonlyToggleWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)
