from django.urls import path
from .views import (
    NotificationListView, NotificationDetailView, UnreadCountView,
    MarkReadView, MarkAllReadView, NotificationManageListView, CreateBroadcastView,
)

urlpatterns = [
    # User-facing (no special permission, just IsAuthenticated)
    path("", NotificationListView.as_view(), name="notification-list"),
    path("unread-count/", UnreadCountView.as_view(), name="notification-unread-count"),
    path("<uuid:pk>/read/", MarkReadView.as_view(), name="notification-read"),
    path("read-all/", MarkAllReadView.as_view(), name="notification-read-all"),
    # Admin management (requires notifications permissions)
    path("manage/", NotificationManageListView.as_view(), name="notification-manage-list"),
    path("manage/create/", CreateBroadcastView.as_view(), name="notification-create"),
    # Detail (user-facing, IsAuthenticated)
    path("<uuid:pk>/", NotificationDetailView.as_view(), name="notification-detail"),
]
