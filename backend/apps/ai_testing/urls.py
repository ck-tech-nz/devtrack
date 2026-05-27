from django.urls import path

from .views import (
    BrowserArtifactDetailView,
    ProjectEnvironmentDetailView,
    ProjectEnvironmentListCreateView,
    TestFlowDetailView,
    TestFlowListCreateView,
    TestRunCancelView,
    TestRunCreateIssueView,
    TestRunDetailView,
    TestRunListCreateView,
    TestRunArtifactsView,
    TestRunStepsView,
)


urlpatterns = [
    path("environments/", ProjectEnvironmentListCreateView.as_view(), name="ai-testing-environments"),
    path("environments/<int:pk>/", ProjectEnvironmentDetailView.as_view(), name="ai-testing-environment-detail"),
    path("flows/", TestFlowListCreateView.as_view(), name="ai-testing-flows"),
    path("flows/<int:pk>/", TestFlowDetailView.as_view(), name="ai-testing-flow-detail"),
    path("runs/", TestRunListCreateView.as_view(), name="ai-testing-runs"),
    path("runs/<int:pk>/", TestRunDetailView.as_view(), name="ai-testing-run-detail"),
    path("runs/<int:pk>/cancel/", TestRunCancelView.as_view(), name="ai-testing-run-cancel"),
    path("runs/<int:pk>/create-issue/", TestRunCreateIssueView.as_view(), name="ai-testing-run-create-issue"),
    path("runs/<int:pk>/steps/", TestRunStepsView.as_view(), name="ai-testing-run-steps"),
    path("runs/<int:pk>/artifacts/", TestRunArtifactsView.as_view(), name="ai-testing-run-artifacts"),
    path("artifacts/<int:pk>/", BrowserArtifactDetailView.as_view(), name="ai-testing-artifact-detail"),
]
