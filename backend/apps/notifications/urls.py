from django.urls import path
from .views import (
    NotificationListView, UnreadCountView,
    MarkReadView, MarkAllReadView, DeleteNotificationView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("unread-count/", UnreadCountView.as_view(), name="notification-unread-count"),
    path("<uuid:pk>/read/", MarkReadView.as_view(), name="notification-read"),
    path("read-all/", MarkAllReadView.as_view(), name="notification-read-all"),
    path("<uuid:pk>/", DeleteNotificationView.as_view(), name="notification-delete"),
]
