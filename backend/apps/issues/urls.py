from django.urls import path
from .views import IssueListCreateView, IssueDetailView, BatchUpdateView

urlpatterns = [
    path("", IssueListCreateView.as_view(), name="issue-list"),
    path("batch-update/", BatchUpdateView.as_view(), name="issue-batch-update"),
    path("<uuid:pk>/", IssueDetailView.as_view(), name="issue-detail"),
]
