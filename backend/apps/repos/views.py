import logging

from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.permissions import FullDjangoModelPermissions
from .models import Repo, GitHubIssue
from .serializers import RepoSerializer, GitHubIssueBriefSerializer, GitHubIssueDetailSerializer
from concurrent.futures import ThreadPoolExecutor
from .services import GitHubSyncService, RepoCloneService

_clone_executor = ThreadPoolExecutor(max_workers=2)

logger = logging.getLogger(__name__)


class RepoListCreateView(generics.ListCreateAPIView):
    serializer_class = RepoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Repo.objects.annotate(
            open_issues_count=Count(
                "github_issues", filter=Q(github_issues__state="open")
            ),
            closed_issues_count=Count(
                "github_issues", filter=Q(github_issues__state="closed")
            ),
        )


class RepoDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = RepoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Repo.objects.annotate(
            open_issues_count=Count(
                "github_issues", filter=Q(github_issues__state="open")
            ),
            closed_issues_count=Count(
                "github_issues", filter=Q(github_issues__state="closed")
            ),
        )


class GitHubIssueListView(generics.ListAPIView):
    serializer_class = GitHubIssueBriefSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = GitHubIssue.objects.select_related("repo").order_by("-github_created_at")
        repo = self.request.query_params.get("repo")
        if repo:
            qs = qs.filter(repo_id=repo)
        state = self.request.query_params.get("state")
        if state:
            qs = qs.filter(state=state)
        return qs


class GitHubIssueDetailView(generics.RetrieveAPIView):
    queryset = GitHubIssue.objects.select_related("repo")
    serializer_class = GitHubIssueDetailSerializer
    permission_classes = [IsAuthenticated]


class RepoSyncView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Repo.objects.none()  # FullDjangoModelPermissions 需要 queryset 确定模型

    def post(self, request, pk):
        try:
            repo = Repo.objects.annotate(
                open_issues_count=Count(
                    "github_issues", filter=Q(github_issues__state="open")
                ),
                closed_issues_count=Count(
                    "github_issues", filter=Q(github_issues__state="closed")
                ),
            ).get(pk=pk)
        except Repo.DoesNotExist:
            return Response(
                {"detail": "仓库不存在"}, status=status.HTTP_404_NOT_FOUND
            )
        try:
            GitHubSyncService().sync_repo(repo)
            repo = Repo.objects.annotate(
                open_issues_count=Count(
                    "github_issues", filter=Q(github_issues__state="open")
                ),
                closed_issues_count=Count(
                    "github_issues", filter=Q(github_issues__state="closed")
                ),
            ).get(pk=pk)
            serializer = RepoSerializer(repo)
            return Response(serializer.data)
        except Exception as e:
            logger.exception("GitHub sync failed for repo %s", pk)
            return Response(
                {"detail": f"GitHub 同步失败: {e}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class RepoCloneView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Repo.objects.none()

    def post(self, request, pk):
        try:
            repo = Repo.objects.get(pk=pk)
        except Repo.DoesNotExist:
            return Response({"detail": "仓库不存在"}, status=status.HTTP_404_NOT_FOUND)
        if repo.clone_status == "cloning":
            return Response(
                {"detail": "克隆任务进行中", "clone_status": "cloning"},
                status=status.HTTP_409_CONFLICT,
            )
        branch = request.data.get("branch")
        _clone_executor.submit(RepoCloneService().clone_or_pull, repo, branch)
        return Response(
            {"detail": "克隆任务已启动", "clone_status": "cloning"},
            status=status.HTTP_202_ACCEPTED,
        )


class RepoGitLogView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Repo.objects.none()

    def get(self, request, pk):
        try:
            repo = Repo.objects.get(pk=pk)
        except Repo.DoesNotExist:
            return Response({"detail": "仓库不存在"}, status=status.HTTP_404_NOT_FOUND)
        if repo.clone_status != "cloned":
            return Response({"detail": "请先同步代码"}, status=status.HTTP_400_BAD_REQUEST)
        limit = min(int(request.query_params.get("limit", 50)), 200)
        commits = RepoCloneService().get_log(repo, limit=limit)
        return Response(commits)


class RepoBranchesView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Repo.objects.none()

    def get(self, request, pk):
        try:
            repo = Repo.objects.get(pk=pk)
        except Repo.DoesNotExist:
            return Response({"detail": "仓库不存在"}, status=status.HTTP_404_NOT_FOUND)
        if repo.clone_status != "cloned":
            return Response({"detail": "请先同步代码"}, status=status.HTTP_400_BAD_REQUEST)
        branches = RepoCloneService().get_branches(repo)
        return Response(branches)
