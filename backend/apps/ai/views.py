from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.permissions import FullDjangoModelPermissions
from .models import Analysis
from .services import AIAnalysisService, AIConfigurationError


class InsightsView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Analysis.objects.none()

    def get(self, request):
        analysis_type = request.query_params.get("type", "team_insights")
        try:
            analysis = AIAnalysisService().get_or_run(
                analysis_type, Analysis.TriggerType.PAGE_OPEN, user=request.user
            )
        except AIConfigurationError as e:
            return Response({"detail": str(e)}, status=503)
        return Response({
            "status": analysis.status,
            "updated_at": analysis.updated_at,
            "is_fresh": analysis.status == Analysis.Status.DONE,
            "result": analysis.parsed_result,
            "error_message": analysis.error_message,
        })


class InsightsRefreshView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Analysis.objects.none()

    def post(self, request):
        analysis_type = request.data.get("type", "team_insights")
        try:
            analysis = AIAnalysisService()._run(
                analysis_type, Analysis.TriggerType.MANUAL, user=request.user, data_hash=""
            )
        except AIConfigurationError as e:
            return Response({"detail": str(e)}, status=503)
        except Exception:
            failed = Analysis.objects.filter(
                analysis_type=analysis_type, status=Analysis.Status.FAILED
            ).order_by("-created_at").first()
            if failed:
                return Response({
                    "status": failed.status,
                    "updated_at": failed.updated_at,
                    "error_message": failed.error_message,
                })
            return Response({"detail": "分析失败"}, status=500)
        return Response({
            "status": analysis.status,
            "updated_at": analysis.updated_at,
            "is_fresh": True,
            "result": analysis.parsed_result,
        })


class SyncGitHubView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        from apps.repos.services import GitHubSyncService
        GitHubSyncService().sync_all()
        return Response({"detail": "同步完成"})
