from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Notification, NotificationRecipient
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(
            recipients__user=self.request.user,
            recipients__is_deleted=False,
        ).select_related("source_user", "source_issue")
        is_read = self.request.query_params.get("is_read")
        if is_read is not None:
            qs = qs.filter(recipients__is_read=is_read.lower() == "true")
        return qs.order_by("-created_at")

    def get_serializer(self, *args, **kwargs):
        """Attach the recipient record to each notification for the serializer."""
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
            notif = instance
            notif.recipient = NotificationRecipient.objects.filter(
                user=self.request.user, notification=notif,
            ).first()
        return super().get_serializer(*args, **kwargs)


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = NotificationRecipient.objects.filter(
            user=request.user, is_read=False, is_deleted=False,
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
