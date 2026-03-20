from django.urls import path
from .views import (
    ProjectListCreateView,
    ProjectDetailView,
    ProjectMemberListCreateView,
    ProjectMemberDeleteView,
    ProjectIssuesView,
)

urlpatterns = [
    path("", ProjectListCreateView.as_view(), name="project-list"),
    path("<uuid:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path("<uuid:project_pk>/members/", ProjectMemberListCreateView.as_view(), name="project-members"),
    path("<uuid:project_pk>/members/<uuid:user_pk>/", ProjectMemberDeleteView.as_view(), name="project-member-delete"),
    path("<uuid:project_pk>/issues/", ProjectIssuesView.as_view(), name="project-issues"),
]
