from django.urls import path
from .views import (
    IssueListCreateView, IssueDetailView, BatchUpdateView,
    IssueGitHubCreateView, IssueGitHubLinkView, IssueCloseWithGitHubView,
)

urlpatterns = [
    path("", IssueListCreateView.as_view(), name="issue-list"),
    path("batch-update/", BatchUpdateView.as_view(), name="issue-batch-update"),
    path("<int:pk>/", IssueDetailView.as_view(), name="issue-detail"),
    path("<int:pk>/github-create/", IssueGitHubCreateView.as_view(), name="issue-github-create"),
    path("<int:pk>/github-link/", IssueGitHubLinkView.as_view(), name="issue-github-link"),
    path("<int:pk>/close-with-github/", IssueCloseWithGitHubView.as_view(), name="issue-close-with-github"),
]
