from django.urls import path
from .views import SiteSettingsView, LabelSettingsView
from .backup_views import (
    BackupListView, BackupCreateView, BackupDownloadView, BackupDeleteView,
)

urlpatterns = [
    path("", SiteSettingsView.as_view(), name="site-settings"),
    path("labels/", LabelSettingsView.as_view(), name="label-settings"),
    path("backups/", BackupListView.as_view(), name="backup-list"),
    path("backups/create/", BackupCreateView.as_view(), name="backup-create"),
    path("backups/<int:pk>/download/", BackupDownloadView.as_view(), name="backup-download"),
    path("backups/<int:pk>/", BackupDeleteView.as_view(), name="backup-delete"),
]
