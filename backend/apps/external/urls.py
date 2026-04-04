from django.urls import path
from .views import ExternalIssueListCreateView, ExternalIssueDetailView
from .views_docs import ExternalAPIDocsView, ExternalAPITestView

urlpatterns = [
    path("issues/", ExternalIssueListCreateView.as_view(), name="external-issue-list"),
    path("issues/<int:pk>/", ExternalIssueDetailView.as_view(), name="external-issue-detail"),
    path("docs/", ExternalAPIDocsView.as_view(), name="external-api-docs"),
    path("test-key/", ExternalAPITestView.as_view(), name="external-api-test-key"),
]
