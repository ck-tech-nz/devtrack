from django.urls import path
from .views import (
    RepoListCreateView, RepoDetailView, GitHubIssueListView,
    RepoSyncView, GitHubIssueDetailView,
    RepoCloneView, RepoGitLogView, RepoBranchesView,
)

urlpatterns = [
    path("", RepoListCreateView.as_view(), name="repo-list"),
    path("github-issues/", GitHubIssueListView.as_view(), name="github-issue-list"),
    path("github-issues/<int:pk>/", GitHubIssueDetailView.as_view(), name="github-issue-detail"),
    path("<int:pk>/sync/", RepoSyncView.as_view(), name="repo-sync"),
    path("<int:pk>/clone/", RepoCloneView.as_view(), name="repo-clone"),
    path("<int:pk>/git-log/", RepoGitLogView.as_view(), name="repo-git-log"),
    path("<int:pk>/branches/", RepoBranchesView.as_view(), name="repo-branches"),
    path("<int:pk>/", RepoDetailView.as_view(), name="repo-detail"),
]
