from django.urls import path
from .views import RepoListCreateView, RepoDetailView

urlpatterns = [
    path("", RepoListCreateView.as_view(), name="repo-list"),
    path("<uuid:pk>/", RepoDetailView.as_view(), name="repo-detail"),
]
