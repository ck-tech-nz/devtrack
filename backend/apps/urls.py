from django.urls import path, include

urlpatterns = [
    path("auth/", include("apps.users.auth_urls")),
    path("settings/", include("apps.settings.urls")),
    path("users/", include("apps.users.urls")),
    path("projects/", include("apps.projects.urls")),
    path("issues/", include("apps.issues.urls")),
    path("dashboard/", include("apps.issues.dashboard_urls")),
    path("repos/", include("apps.repos.urls")),
]
