from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.permissions import FullDjangoModelPermissions
from .models import Analysis, LLMConfig, Prompt
from .client import LLMClient


class InsightsView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Analysis.objects.none()

    def get(self, request):
        analysis_type = request.query_params.get("type", "team_insights")

        # 返回最新缓存结果（如果存在且未过期）
        latest = (
            Analysis.objects.filter(analysis_type=analysis_type, status=Analysis.Status.DONE)
            .order_by("-created_at")
            .first()
        )
        if latest:
            from .services import AIAnalysisService
            if not AIAnalysisService()._is_stale(latest):
                return Response({
                    "status": latest.status,
                    "updated_at": latest.updated_at,
                    "is_fresh": True,
                    "result": latest.parsed_result,
                    "error_message": latest.error_message,
                })

        # 在派发任务前检查配置是否存在
        has_prompt = Prompt.objects.filter(slug=analysis_type, is_active=True).exists()
        has_llm = LLMConfig.objects.filter(is_active=True).exists()
        if not has_prompt or not has_llm:
            return Response(
                {"detail": "AI 服务未配置"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # 派发异步任务
        from .tasks import run_team_insights
        run_team_insights.delay()

        # 若有旧结果则返回，否则返回 pending
        if latest:
            return Response({
                "status": "running",
                "updated_at": latest.updated_at,
                "is_fresh": False,
                "result": latest.parsed_result,
                "error_message": None,
            }, status=status.HTTP_202_ACCEPTED)

        return Response({
            "status": "pending",
            "updated_at": None,
            "is_fresh": False,
            "result": None,
            "error_message": None,
        }, status=status.HTTP_202_ACCEPTED)


class InsightsRefreshView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Analysis.objects.none()

    def post(self, request):
        from .tasks import refresh_team_insights
        refresh_team_insights.delay(user_id=request.user.id)
        return Response({
            "status": "pending",
            "message": "已提交刷新请求",
        }, status=status.HTTP_202_ACCEPTED)


class AnalysisStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from .models import Analysis
        try:
            analysis = Analysis.objects.get(pk=pk)
        except Analysis.DoesNotExist:
            return Response({"detail": "分析记录不存在"}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            "id": analysis.id,
            "status": analysis.status,
            "error_message": analysis.error_message,
        })


class GenerateNicknameView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        import json as _json
        username = (request.data.get("username") or "未知").strip()

        prompt = Prompt.objects.filter(slug="generate_nickname", is_active=True).first()
        if prompt is None:
            return Response({"detail": "昵称生成提示词未配置（slug: generate_nickname）"}, status=503)

        llm_config = prompt.llm_config
        if llm_config is None:
            llm_config = LLMConfig.objects.filter(is_default=True, is_active=True).first()
        if llm_config is None:
            llm_config = LLMConfig.objects.filter(is_active=True).first()
        if llm_config is None:
            return Response({"detail": "AI 服务未配置"}, status=503)

        raw_exclude = request.data.get("exclude") or []
        if isinstance(raw_exclude, str):
            raw_exclude = [raw_exclude] if raw_exclude.strip() else []
        exclude_list = [s.strip() for s in raw_exclude if s.strip()]

        try:
            user_prompt = prompt.user_prompt_template.format(username=username)
            if exclude_list:
                quoted = "、".join(f"「{n}」" for n in exclude_list)
                user_prompt += f"\n注意：以下昵称已被使用，必须生成一个完全不同的新昵称，不能与这些重复：{quoted}。"
        except KeyError as e:
            return Response({"detail": f"提示词模板占位符错误: {e}"}, status=500)

        try:
            client = LLMClient(llm_config)
            raw = client.complete(
                model=prompt.llm_model,
                system_prompt=prompt.system_prompt,
                user_prompt=user_prompt,
                temperature=prompt.temperature,
            )
            nickname = _json.loads(raw).get("nickname", raw.strip())
            return Response({"nickname": nickname})
        except Exception as e:
            return Response({"detail": f"生成失败：{e}"}, status=500)


class SyncGitHubView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        from apps.repos.services import GitHubSyncService
        GitHubSyncService().sync_all()
        return Response({"detail": "同步完成"})
