from django.urls import path
from .views import InsightsView, InsightsRefreshView, SyncGitHubView

urlpatterns = [
    path("insights/", InsightsView.as_view(), name="ai-insights"),
    path("insights/refresh/", InsightsRefreshView.as_view(), name="ai-insights-refresh"),
    path("sync-github/", SyncGitHubView.as_view(), name="ai-sync-github"),
]
