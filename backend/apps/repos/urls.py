from django.urls import path
from .views import RepoListCreateView, RepoDetailView

urlpatterns = [
    path("", RepoListCreateView.as_view(), name="repo-list"),
    path("<int:pk>/", RepoDetailView.as_view(), name="repo-detail"),
]
