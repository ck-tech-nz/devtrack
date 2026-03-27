from django.urls import path
from .views import InsightsView, InsightsRefreshView, SyncGitHubView, AnalysisStatusView

urlpatterns = [
    path("insights/", InsightsView.as_view(), name="ai-insights"),
    path("insights/refresh/", InsightsRefreshView.as_view(), name="ai-insights-refresh"),
    path("sync-github/", SyncGitHubView.as_view(), name="ai-sync-github"),
    path("analysis/<int:pk>/status/", AnalysisStatusView.as_view(), name="analysis-status"),
]
