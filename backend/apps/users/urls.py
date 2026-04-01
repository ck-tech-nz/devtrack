from django.urls import path
from .views import UserListView, UserDetailView, UserChoicesView

urlpatterns = [
    path("choices/", UserChoicesView.as_view(), name="user-choices"),
    path("", UserListView.as_view(), name="user-list"),
    path("<int:pk>/", UserDetailView.as_view(), name="user-detail"),
]
