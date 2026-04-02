from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.permissions import FullDjangoModelPermissions
from .models import Notification, NotificationRecipient
from .serializers import NotificationSerializer, NotificationManageSerializer

User = get_user_model()


# ──────────────────────────────────────────────
# User-facing endpoints (IsAuthenticated only)
# ──────────────────────────────────────────────

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(
            recipients__user=self.request.user,
            recipients__is_deleted=False,
            is_draft=False,
        ).select_related("source_user", "source_issue").distinct()
        is_read = self.request.query_params.get("is_read")
        if is_read is not None:
            qs = qs.filter(recipients__is_read=is_read.lower() == "true")
        return qs.order_by("-created_at")

    def get_serializer(self, *args, **kwargs):
        instance = kwargs.get("instance") or (args[0] if args else None)
        if instance is not None and hasattr(instance, "__iter__"):
            recipient_map = {
                r.notification_id: r
                for r in NotificationRecipient.objects.filter(
                    user=self.request.user,
                    notification__in=instance,
                )
            }
            for notif in instance:
                notif.recipient = recipient_map.get(notif.id)
        elif instance is not None:
            instance.recipient = NotificationRecipient.objects.filter(
                user=self.request.user, notification=instance,
            ).first()
        return super().get_serializer(*args, **kwargs)


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = NotificationRecipient.objects.filter(
            user=request.user, is_read=False, is_deleted=False,
            notification__is_draft=False,
        ).count()
        return Response({"count": count})


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            recipient = NotificationRecipient.objects.get(
                notification_id=pk, user=request.user,
            )
        except NotificationRecipient.DoesNotExist:
            return Response({"detail": "通知不存在"}, status=status.HTTP_404_NOT_FOUND)
        recipient.is_read = True
        recipient.read_at = timezone.now()
        recipient.save(update_fields=["is_read", "read_at"])
        return Response({"detail": "已标记已读"})


class MarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = NotificationRecipient.objects.filter(
            user=request.user, is_read=False, is_deleted=False,
        ).update(is_read=True, read_at=timezone.now())
        return Response({"updated": updated})


class NotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            recipient = NotificationRecipient.objects.select_related(
                "notification__source_user", "notification__source_issue",
            ).get(notification_id=pk, user=request.user)
        except NotificationRecipient.DoesNotExist:
            return Response({"detail": "通知不存在"}, status=status.HTTP_404_NOT_FOUND)
        notif = recipient.notification
        notif.recipient = recipient
        serializer = NotificationSerializer(notif)
        return Response(serializer.data)

    def delete(self, request, pk):
        try:
            recipient = NotificationRecipient.objects.get(
                notification_id=pk, user=request.user,
            )
        except NotificationRecipient.DoesNotExist:
            return Response({"detail": "通知不存在"}, status=status.HTTP_404_NOT_FOUND)
        recipient.is_deleted = True
        recipient.save(update_fields=["is_deleted"])
        return Response(status=status.HTTP_204_NO_CONTENT)


# ──────────────────────────────────────────────
# Admin manage endpoints (requires permissions)
# ──────────────────────────────────────────────

def _generate_recipients(notification):
    """Generate NotificationRecipient rows based on target_type. Idempotent."""
    if notification.target_type == Notification.TargetType.ALL:
        users = User.objects.filter(is_active=True)
    elif notification.target_type == Notification.TargetType.GROUP and notification.target_group:
        users = notification.target_group.user_set.filter(is_active=True)
    elif notification.target_type == Notification.TargetType.USER:
        users = notification.target_users.filter(is_active=True)
    else:
        return 0
    recipients = [NotificationRecipient(notification=notification, user=u) for u in users]
    NotificationRecipient.objects.bulk_create(recipients, ignore_conflicts=True)
    return len(recipients)


class ManageListView(generics.ListAPIView):
    serializer_class = NotificationManageSerializer
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Notification.objects.all()

    def get_queryset(self):
        return Notification.objects.select_related(
            "source_user", "target_group",
        ).order_by("-created_at")


class ManageDetailView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Notification.objects.none()

    def get(self, request, pk):
        try:
            notif = Notification.objects.select_related(
                "source_user", "target_group",
            ).prefetch_related("target_users").get(pk=pk)
        except Notification.DoesNotExist:
            return Response({"detail": "通知不存在"}, status=status.HTTP_404_NOT_FOUND)
        serializer = NotificationManageSerializer(notif)
        return Response(serializer.data)

    def delete(self, request, pk):
        try:
            notif = Notification.objects.get(pk=pk)
        except Notification.DoesNotExist:
            return Response({"detail": "通知不存在"}, status=status.HTTP_404_NOT_FOUND)
        notif.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ManageCreateView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Notification.objects.none()

    def post(self, request):
        title = request.data.get("title", "").strip()
        if not title:
            return Response({"detail": "标题不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        content = request.data.get("content", "")
        target_type = request.data.get("target_type", "all")
        is_draft = request.data.get("is_draft", False)

        notification = Notification.objects.create(
            notification_type=Notification.Type.BROADCAST,
            title=title,
            content=content,
            source_user=request.user,
            target_type=target_type,
            target_group_id=request.data.get("target_group") or None,
            is_draft=is_draft,
        )

        # Set target users for user-type notifications
        target_user_ids = request.data.get("target_user_ids", [])
        if target_type == Notification.TargetType.USER and target_user_ids:
            notification.target_users.set(target_user_ids)

        recipient_count = 0
        if not is_draft:
            recipient_count = _generate_recipients(notification)

        return Response(
            {"id": str(notification.id), "recipients": recipient_count},
            status=status.HTTP_201_CREATED,
        )


class ManageUpdateView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Notification.objects.none()

    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk)
        except Notification.DoesNotExist:
            return Response({"detail": "通知不存在"}, status=status.HTTP_404_NOT_FOUND)

        was_draft = notification.is_draft

        # Update fields
        for field in ("title", "content", "target_type", "is_draft"):
            if field in request.data:
                setattr(notification, field, request.data[field])

        if "target_group" in request.data:
            notification.target_group_id = request.data["target_group"] or None

        notification.save()

        # Update target users
        if "target_user_ids" in request.data:
            notification.target_users.set(request.data["target_user_ids"])

        # If publishing (draft → not draft), generate recipients
        recipient_count = notification.recipients.count()
        if was_draft and not notification.is_draft:
            recipient_count = _generate_recipients(notification)

        serializer = NotificationManageSerializer(notification)
        data = serializer.data
        data["recipient_count"] = recipient_count
        return Response(data)


class ManagePublishView(APIView):
    """Publish a draft notification: set is_draft=False and generate recipients."""
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Notification.objects.none()

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk)
        except Notification.DoesNotExist:
            return Response({"detail": "通知不存在"}, status=status.HTTP_404_NOT_FOUND)

        if not notification.is_draft:
            return Response({"detail": "该通知已发布"}, status=status.HTTP_400_BAD_REQUEST)

        notification.is_draft = False
        notification.save(update_fields=["is_draft"])
        recipient_count = _generate_recipients(notification)

        return Response({"id": str(notification.id), "recipients": recipient_count})
