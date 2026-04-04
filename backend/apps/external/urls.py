from django.urls import path
from .views import ExternalIssueListCreateView, ExternalIssueDetailView

urlpatterns = [
    path("issues/", ExternalIssueListCreateView.as_view(), name="external-issue-list"),
    path("issues/<int:pk>/", ExternalIssueDetailView.as_view(), name="external-issue-detail"),
]
