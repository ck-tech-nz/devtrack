from django.urls import path
from .views import (
    KPITeamView, KPIUserSummaryView, KPIUserIssuesView, KPIUserCommitsView,
    KPIUserTrendsView, KPIUserSuggestionsView, KPIRefreshView,
    KPIMeSummaryView, KPIMeIssuesView, KPIMeCommitsView, KPIMeTrendsView, KPIMeSuggestionsView,
)

urlpatterns = [
    path("team/", KPITeamView.as_view(), name="kpi-team"),
    path("refresh/", KPIRefreshView.as_view(), name="kpi-refresh"),
    path("me/summary/", KPIMeSummaryView.as_view(), name="kpi-me-summary"),
    path("me/issues/", KPIMeIssuesView.as_view(), name="kpi-me-issues"),
    path("me/commits/", KPIMeCommitsView.as_view(), name="kpi-me-commits"),
    path("me/trends/", KPIMeTrendsView.as_view(), name="kpi-me-trends"),
    path("me/suggestions/", KPIMeSuggestionsView.as_view(), name="kpi-me-suggestions"),
    path("users/<int:user_id>/summary/", KPIUserSummaryView.as_view(), name="kpi-user-summary"),
    path("users/<int:user_id>/issues/", KPIUserIssuesView.as_view(), name="kpi-user-issues"),
    path("users/<int:user_id>/commits/", KPIUserCommitsView.as_view(), name="kpi-user-commits"),
    path("users/<int:user_id>/trends/", KPIUserTrendsView.as_view(), name="kpi-user-trends"),
    path("users/<int:user_id>/suggestions/", KPIUserSuggestionsView.as_view(), name="kpi-user-suggestions"),
]
