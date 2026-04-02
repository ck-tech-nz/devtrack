from django.urls import path
from .views import (
    NotificationListView, NotificationDetailView, UnreadCountView,
    MarkReadView, MarkAllReadView, CreateBroadcastView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("unread-count/", UnreadCountView.as_view(), name="notification-unread-count"),
    path("create/", CreateBroadcastView.as_view(), name="notification-create"),
    path("<uuid:pk>/read/", MarkReadView.as_view(), name="notification-read"),
    path("read-all/", MarkAllReadView.as_view(), name="notification-read-all"),
    path("<uuid:pk>/", NotificationDetailView.as_view(), name="notification-detail"),
]
