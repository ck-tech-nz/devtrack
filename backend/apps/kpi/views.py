"""
KPI API views
"""

from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.permissions import FullDjangoModelPermissions
from .models import KPISnapshot
from .serializers import KPITeamDeveloperSerializer, KPISummarySerializer
from .services import KPIService

User = get_user_model()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _parse_period(request) -> tuple[date, date]:
    """Parse period from query params. Returns (start, end).

    Supports:
      ?period=week   — current week (Mon-Sun)
      ?period=month  — current month (default)
      ?period=quarter — current quarter
      ?start=YYYY-MM-DD&end=YYYY-MM-DD — custom range
    """
    start_str = request.query_params.get("start")
    end_str = request.query_params.get("end")
    if start_str and end_str:
        return date.fromisoformat(start_str), date.fromisoformat(end_str)

    today = timezone.now().date()
    period = request.query_params.get("period", "month")

    if period == "week":
        start = today - timedelta(days=today.weekday())  # Monday
        end = start + timedelta(days=6)
        return start, min(end, today)
    elif period == "quarter":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=quarter_start_month, day=1)
        return start, today
    else:  # month (default)
        start = today.replace(day=1)
        return start, today


def _has_kpi_access(request, user_id: int) -> bool:
    """Return True if the requesting user can view the given user_id's KPI."""
    if request.user.has_perm("kpi.view_kpisnapshot"):
        return True
    if request.user.id == user_id and request.user.has_perm("kpi.view_own_kpi"):
        return True
    return False


def _get_snapshot(user_id: int, period_start: date, period_end: date) -> KPISnapshot | None:
    """Get the latest snapshot for a user in the given period."""
    return (
        KPISnapshot.objects.filter(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
        )
        .select_related("user")
        .first()
    )


# ------------------------------------------------------------------
# Team dashboard
# ------------------------------------------------------------------

class KPITeamView(APIView):
    """GET /api/kpi/team/ — team dashboard (managers only)."""

    permission_classes = [FullDjangoModelPermissions]
    queryset = KPISnapshot.objects.none()  # needed for FullDjangoModelPermissions

    def get(self, request):
        period_start, period_end = _parse_period(request)
        snapshots = (
            KPISnapshot.objects.filter(
                period_start=period_start,
                period_end=period_end,
            )
            .select_related("user")
            .order_by("-scores__overall")
        )
        serializer = KPITeamDeveloperSerializer(snapshots, many=True)
        return Response({
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "developers": serializer.data,
        })


# ------------------------------------------------------------------
# Individual KPI views (by user_id)
# ------------------------------------------------------------------

class KPIUserSummaryView(APIView):
    """GET /api/kpi/users/{user_id}/summary/"""

    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if not _has_kpi_access(request, user_id):
            return Response({"detail": "权限不足"}, status=status.HTTP_403_FORBIDDEN)

        period_start, period_end = _parse_period(request)
        snap = _get_snapshot(user_id, period_start, period_end)
        if not snap:
            return Response({"detail": "未找到 KPI 数据"}, status=status.HTTP_404_NOT_FOUND)

        serializer = KPISummarySerializer(snap)
        return Response(serializer.data)


class KPIUserIssuesView(APIView):
    """GET /api/kpi/users/{user_id}/issues/"""

    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if not _has_kpi_access(request, user_id):
            return Response({"detail": "权限不足"}, status=status.HTTP_403_FORBIDDEN)

        period_start, period_end = _parse_period(request)
        snap = _get_snapshot(user_id, period_start, period_end)
        if not snap:
            return Response({"detail": "未找到 KPI 数据"}, status=status.HTTP_404_NOT_FOUND)

        return Response(snap.issue_metrics)


class KPIUserCommitsView(APIView):
    """GET /api/kpi/users/{user_id}/commits/"""

    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if not _has_kpi_access(request, user_id):
            return Response({"detail": "权限不足"}, status=status.HTTP_403_FORBIDDEN)

        period_start, period_end = _parse_period(request)
        snap = _get_snapshot(user_id, period_start, period_end)
        if not snap:
            return Response({"detail": "未找到 KPI 数据"}, status=status.HTTP_404_NOT_FOUND)

        return Response(snap.commit_metrics)


class KPIUserTrendsView(APIView):
    """GET /api/kpi/users/{user_id}/trends/ — last N snapshots."""

    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if not _has_kpi_access(request, user_id):
            return Response({"detail": "权限不足"}, status=status.HTTP_403_FORBIDDEN)

        limit = int(request.query_params.get("limit", 6))
        snapshots = (
            KPISnapshot.objects.filter(user_id=user_id)
            .order_by("period_end", "computed_at")[:limit]
        )
        data = [
            {
                "period_start": s.period_start.isoformat(),
                "period_end": s.period_end.isoformat(),
                "scores": s.scores,
                "rankings": s.rankings,
                "computed_at": s.computed_at.isoformat(),
            }
            for s in snapshots
        ]
        return Response(data)


class KPIUserSuggestionsView(APIView):
    """GET /api/kpi/users/{user_id}/suggestions/"""

    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if not _has_kpi_access(request, user_id):
            return Response({"detail": "权限不足"}, status=status.HTTP_403_FORBIDDEN)

        period_start, period_end = _parse_period(request)
        snap = _get_snapshot(user_id, period_start, period_end)
        if not snap:
            return Response({"detail": "未找到 KPI 数据"}, status=status.HTTP_404_NOT_FOUND)

        return Response(snap.suggestions)


# ------------------------------------------------------------------
# Refresh
# ------------------------------------------------------------------

class KPIRefreshView(APIView):
    """POST /api/kpi/refresh/ — trigger KPI recalculation."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.has_perm("kpi.refresh_kpi"):
            return Response({"detail": "权限不足"}, status=status.HTTP_403_FORBIDDEN)

        period_start, period_end = _parse_period(request)
        result = KPIService().refresh(period_start=period_start, period_end=period_end)
        return Response({
            "status": "completed",
            "computed_at": result["computed_at"],
            "user_count": result["user_count"],
        })


# ------------------------------------------------------------------
# /me shortcuts
# ------------------------------------------------------------------

class KPIMeSummaryView(APIView):
    """GET /api/kpi/me/summary/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_kpi_access(request, request.user.id):
            return Response({"detail": "权限不足"}, status=status.HTTP_403_FORBIDDEN)

        period_start, period_end = _parse_period(request)
        snap = _get_snapshot(request.user.id, period_start, period_end)
        if not snap:
            return Response({"detail": "未找到 KPI 数据"}, status=status.HTTP_404_NOT_FOUND)

        serializer = KPISummarySerializer(snap)
        return Response(serializer.data)


class KPIMeIssuesView(APIView):
    """GET /api/kpi/me/issues/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_kpi_access(request, request.user.id):
            return Response({"detail": "权限不足"}, status=status.HTTP_403_FORBIDDEN)

        period_start, period_end = _parse_period(request)
        snap = _get_snapshot(request.user.id, period_start, period_end)
        if not snap:
            return Response({"detail": "未找到 KPI 数据"}, status=status.HTTP_404_NOT_FOUND)

        return Response(snap.issue_metrics)


class KPIMeCommitsView(APIView):
    """GET /api/kpi/me/commits/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_kpi_access(request, request.user.id):
            return Response({"detail": "权限不足"}, status=status.HTTP_403_FORBIDDEN)

        period_start, period_end = _parse_period(request)
        snap = _get_snapshot(request.user.id, period_start, period_end)
        if not snap:
            return Response({"detail": "未找到 KPI 数据"}, status=status.HTTP_404_NOT_FOUND)

        return Response(snap.commit_metrics)


class KPIMeTrendsView(APIView):
    """GET /api/kpi/me/trends/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_kpi_access(request, request.user.id):
            return Response({"detail": "权限不足"}, status=status.HTTP_403_FORBIDDEN)

        limit = int(request.query_params.get("limit", 6))
        snapshots = (
            KPISnapshot.objects.filter(user_id=request.user.id)
            .order_by("period_end", "computed_at")[:limit]
        )
        data = [
            {
                "period_start": s.period_start.isoformat(),
                "period_end": s.period_end.isoformat(),
                "scores": s.scores,
                "rankings": s.rankings,
                "computed_at": s.computed_at.isoformat(),
            }
            for s in snapshots
        ]
        return Response(data)


class KPIMeSuggestionsView(APIView):
    """GET /api/kpi/me/suggestions/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_kpi_access(request, request.user.id):
            return Response({"detail": "权限不足"}, status=status.HTTP_403_FORBIDDEN)

        period_start, period_end = _parse_period(request)
        snap = _get_snapshot(request.user.id, period_start, period_end)
        if not snap:
            return Response({"detail": "未找到 KPI 数据"}, status=status.HTTP_404_NOT_FOUND)

        return Response(snap.suggestions)
