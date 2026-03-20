from datetime import timedelta
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.permissions import FullDjangoModelPermissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Avg, F
from django.db.models.functions import TruncDate
from .models import Issue, Activity
from .serializers import (
    IssueListSerializer, IssueDetailSerializer,
    IssueCreateUpdateSerializer, BatchUpdateSerializer,
    ActivitySerializer,
)

User = get_user_model()


class IssueListCreateView(generics.ListCreateAPIView):
    queryset = Issue.objects.select_related("reporter", "assignee")
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["priority", "status", "assignee", "project"]
    search_fields = ["title"]
    ordering_fields = ["created_at", "priority", "updated_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return IssueCreateUpdateSerializer
        return IssueListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        labels = self.request.query_params.get("labels")
        if labels:
            qs = qs.filter(labels__contains=[labels])
        return qs


class IssueDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Issue.objects.select_related("reporter", "assignee")
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return IssueCreateUpdateSerializer
        return IssueDetailSerializer


class BatchUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BatchUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        issues = Issue.objects.filter(id__in=data["ids"])
        count = issues.count()

        if data["action"] == "assign":
            user = User.objects.get(id=data["value"])
            issues.update(assignee=user)
        elif data["action"] == "set_priority":
            issues.update(priority=data["value"])

        return Response({"updated": count})


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        return Response({
            "total": Issue.objects.count(),
            "pending": Issue.objects.filter(status="待处理").count(),
            "in_progress": Issue.objects.filter(status="进行中").count(),
            "resolved_this_week": Issue.objects.filter(resolved_at__gte=week_start).count(),
        })


class DashboardTrendsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        start = today - timedelta(days=29)
        dates = [start + timedelta(days=i) for i in range(30)]

        created_counts = dict(
            Issue.objects.filter(created_at__date__gte=start)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .values_list("date", "count")
        )
        resolved_counts = dict(
            Issue.objects.filter(resolved_at__date__gte=start)
            .annotate(date=TruncDate("resolved_at"))
            .values("date")
            .annotate(count=Count("id"))
            .values_list("date", "count")
        )

        return Response([
            {
                "date": d.isoformat(),
                "created": created_counts.get(d, 0),
                "resolved": resolved_counts.get(d, 0),
            }
            for d in dates
        ])


class DashboardPriorityDistributionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = (
            Issue.objects.values("priority")
            .annotate(count=Count("id"))
            .order_by("priority")
        )
        return Response(list(data))


class DashboardLeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        data = (
            Issue.objects.filter(status="已解决", resolved_at__gte=month_start)
            .values("assignee")
            .annotate(
                monthly_resolved_count=Count("id"),
                avg_resolution_hours=Avg(F("resolved_at") - F("created_at")),
            )
            .order_by("-monthly_resolved_count")[:5]
        )
        result = []
        for entry in data:
            user = User.objects.filter(id=entry["assignee"]).first()
            if user:
                avg_hours = entry["avg_resolution_hours"]
                if avg_hours:
                    avg_hours = round(avg_hours.total_seconds() / 3600, 1)
                result.append({
                    "user_id": str(user.id),
                    "user_name": user.name,
                    "monthly_resolved_count": entry["monthly_resolved_count"],
                    "avg_resolution_hours": avg_hours,
                })
        return Response(result)


class DashboardRecentActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        activities = Activity.objects.select_related("user", "issue")[:20]
        return Response(ActivitySerializer(activities, many=True).data)
