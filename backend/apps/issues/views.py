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
from apps.repos.models import Repo, GitHubIssue
from apps.ai.models import Analysis
from apps.ai.services import IssueAnalysisService
from apps.repos.services import GitHubSyncService
from apps.repos.serializers import GitHubIssueBriefSerializer
from .models import Issue, Activity
from .serializers import (
    IssueListSerializer, IssueDetailSerializer,
    IssueCreateUpdateSerializer, BatchUpdateSerializer,
    ActivitySerializer,
)

User = get_user_model()


class IssueListCreateView(generics.ListCreateAPIView):
    queryset = Issue.objects.select_related("reporter", "assignee").prefetch_related("github_issues__repo")
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
        exclude_statuses = self.request.query_params.get("exclude_statuses")
        if exclude_statuses:
            qs = qs.exclude(status__in=exclude_statuses.split(","))
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


class IssueGitHubCreateView(APIView):
    """根据 DevTrack Issue 在 GitHub 上创建 issue 并自动关联。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        issue = Issue.objects.filter(pk=pk).first()
        if not issue:
            return Response({"detail": "问题不存在"}, status=status.HTTP_404_NOT_FOUND)

        repo_id = request.data.get("repo")
        if not repo_id:
            return Response({"detail": "请指定仓库"}, status=status.HTTP_400_BAD_REQUEST)

        repo = Repo.objects.filter(pk=repo_id).first()
        if not repo or not repo.github_token:
            return Response({"detail": "仓库不存在或未配置 Token"}, status=status.HTTP_400_BAD_REQUEST)

        body = f"来自 DevTrack #{issue.pk}: {issue.title}\n\n{issue.description}"
        try:
            svc = GitHubSyncService()
            gh_issue = svc.create_issue(repo, issue.title, body)
        except Exception as e:
            return Response({"detail": f"GitHub 创建失败: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        issue.github_issues.add(gh_issue)
        return Response(GitHubIssueBriefSerializer(gh_issue).data, status=status.HTTP_201_CREATED)


class IssueGitHubLinkView(APIView):
    """关联/解除关联已有的 GitHub Issue。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        issue = Issue.objects.filter(pk=pk).first()
        if not issue:
            return Response({"detail": "问题不存在"}, status=status.HTTP_404_NOT_FOUND)
        gh_ids = request.data.get("github_issue_ids", [])
        gh_issues = GitHubIssue.objects.filter(id__in=gh_ids)
        issue.github_issues.add(*gh_issues)
        return Response({"linked": len(gh_issues)})

    def delete(self, request, pk):
        issue = Issue.objects.filter(pk=pk).first()
        if not issue:
            return Response({"detail": "问题不存在"}, status=status.HTTP_404_NOT_FOUND)
        gh_ids = request.data.get("github_issue_ids", [])
        gh_issues = GitHubIssue.objects.filter(id__in=gh_ids)
        issue.github_issues.remove(*gh_issues)
        return Response({"unlinked": len(gh_issues)})


class IssueAIAnalyzeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        issue = Issue.objects.select_related("repo").filter(pk=pk).first()
        if not issue:
            return Response({"detail": "问题不存在"}, status=status.HTTP_404_NOT_FOUND)
        if not issue.repo:
            return Response({"detail": "请先关联仓库"}, status=status.HTTP_400_BAD_REQUEST)
        if issue.repo.clone_status != "cloned":
            return Response({"detail": "请先同步代码"}, status=status.HTTP_400_BAD_REQUEST)

        svc = IssueAnalysisService()
        existing = svc.get_running_analysis(issue)
        if existing:
            return Response(
                {"analysis_id": existing.id, "status": "running"},
                status=status.HTTP_409_CONFLICT,
            )

        analysis = svc.analyze_async(issue, triggered_by="manual", user=request.user)
        return Response(
            {"analysis_id": analysis.id, "status": "running"},
            status=status.HTTP_202_ACCEPTED,
        )


class IssueAIStatusView(APIView):
    """查询 Issue 是否有正在运行的 AI 分析。"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        issue = Issue.objects.filter(pk=pk).first()
        if not issue:
            return Response({"detail": "问题不存在"}, status=status.HTTP_404_NOT_FOUND)
        svc = IssueAnalysisService()
        running = svc.get_running_analysis(issue)
        if running:
            return Response({"analysis_id": running.id, "status": "running"})
        return Response({"analysis_id": None, "status": "idle"})


class IssueAnalysesView(APIView):
    """GET /api/issues/{id}/analyses/ — 返回该 Issue 的 AI 分析历史"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        issue = Issue.objects.filter(pk=pk).first()
        if not issue:
            return Response({"detail": "问题不存在"}, status=status.HTTP_404_NOT_FOUND)

        analyses = (
            Analysis.objects
            .filter(issue=issue, analysis_type="issue_code_analysis")
            .select_related("triggered_by_user")
            .order_by("-created_at")
        )

        data = []
        for a in analyses:
            results = None
            if a.status == Analysis.Status.DONE and a.parsed_result:
                pr = a.parsed_result
                if "target_field" in pr:
                    results = {pr["target_field"]: pr.get("content", "")}
                else:
                    results = {k: v for k, v in pr.items()
                              if k in ("cause", "solution", "remark") and v}

            data.append({
                "id": a.id,
                "status": a.status,
                "triggered_by": a.triggered_by,
                "triggered_by_user": (
                    a.triggered_by_user.name or a.triggered_by_user.username
                ) if a.triggered_by_user else None,
                "created_at": a.created_at.isoformat(),
                "error_message": a.error_message if a.status == Analysis.Status.FAILED else None,
                "results": results,
            })

        return Response(data)


class IssueCloseWithGitHubView(APIView):
    """关闭 DevTrack Issue，同时关闭关联的 GitHub Issues。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        issue = Issue.objects.filter(pk=pk).first()
        if not issue:
            return Response({"detail": "问题不存在"}, status=status.HTTP_404_NOT_FOUND)

        old_status = issue.status
        issue.status = "已关闭"
        issue.save(update_fields=["status"])

        Activity.objects.create(
            user=request.user, issue=issue, action="closed",
            detail=f"状态从 {old_status} 改为 已关闭",
        )

        # 关闭关联的 GitHub Issues
        svc = GitHubSyncService()
        errors = []
        for gh_issue in issue.github_issues.filter(state=GitHubIssue.STATE_OPEN):
            try:
                svc.close_issue(gh_issue)
            except Exception as e:
                errors.append(f"#{gh_issue.github_id}: {e}")

        result = {"detail": "已关闭", "github_closed": issue.github_issues.count() - len(errors)}
        if errors:
            result["github_errors"] = errors
        return Response(result)
