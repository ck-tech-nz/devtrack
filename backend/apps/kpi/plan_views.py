"""
提升计划 API 视图
"""
from datetime import date

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.permissions import FullDjangoModelPermissions
from apps.tools.storage import upload_image
from .models import ImprovementPlan, ActionItem, ActionItemComment
from .plan_serializers import (
    PlanListSerializer, PlanDetailSerializer,
    ActionItemSerializer, ActionItemCommentSerializer,
)


class PlanListView(APIView):
    """GET /api/kpi/plans/ — 管理员查看团队计划列表。"""
    permission_classes = [FullDjangoModelPermissions]
    queryset = ImprovementPlan.objects.none()

    def get(self, request):
        period = request.query_params.get("period", timezone.now().strftime("%Y-%m"))
        plans = (
            ImprovementPlan.objects.filter(period=period)
            .select_related("user", "reviewed_by")
            .prefetch_related("action_items")
            .order_by("user__name")
        )
        serializer = PlanListSerializer(plans, many=True)
        return Response(serializer.data)


class MyPlanView(APIView):
    """GET /api/kpi/plans/me/ — 员工查看自己的计划。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        current_period = now.strftime("%Y-%m")

        current = (
            ImprovementPlan.objects.filter(
                user=request.user,
                period=current_period,
                status__in=["published", "archived"],
            )
            .prefetch_related("action_items__comments")
            .select_related("reviewed_by")
            .first()
        )

        history = (
            ImprovementPlan.objects.filter(
                user=request.user,
                status="archived",
            )
            .exclude(period=current_period)
            .prefetch_related("action_items")
            .order_by("-period")[:12]
        )

        return Response({
            "current": PlanDetailSerializer(current).data if current else None,
            "history": PlanListSerializer(history, many=True).data,
        })


class PlanDetailView(APIView):
    """GET /api/kpi/plans/{id}/ — 计划详情。"""
    permission_classes = [FullDjangoModelPermissions]
    queryset = ImprovementPlan.objects.none()

    def get(self, request, pk):
        try:
            plan = (
                ImprovementPlan.objects.select_related("user", "reviewed_by")
                .prefetch_related("action_items__comments__author")
                .get(pk=pk)
            )
        except ImprovementPlan.DoesNotExist:
            return Response({"detail": "计划不存在"}, status=status.HTTP_404_NOT_FOUND)
        return Response(PlanDetailSerializer(plan).data)


class PlanPublishView(APIView):
    """POST /api/kpi/plans/{id}/publish/ — 发布计划。"""
    permission_classes = [FullDjangoModelPermissions]
    queryset = ImprovementPlan.objects.none()

    def post(self, request, pk):
        try:
            plan = ImprovementPlan.objects.get(pk=pk)
        except ImprovementPlan.DoesNotExist:
            return Response({"detail": "计划不存在"}, status=status.HTTP_404_NOT_FOUND)
        if plan.status != ImprovementPlan.Status.DRAFT:
            return Response({"detail": "只能发布草案状态的计划"}, status=status.HTTP_400_BAD_REQUEST)
        plan.status = ImprovementPlan.Status.PUBLISHED
        plan.reviewed_by = request.user
        plan.published_at = timezone.now()
        plan.save(update_fields=["status", "reviewed_by", "published_at", "updated_at"])
        return Response(PlanDetailSerializer(plan).data)


class PlanArchiveView(APIView):
    """POST /api/kpi/plans/{id}/archive/ — 归档计划。"""
    permission_classes = [FullDjangoModelPermissions]
    queryset = ImprovementPlan.objects.none()

    def post(self, request, pk):
        try:
            plan = ImprovementPlan.objects.get(pk=pk)
        except ImprovementPlan.DoesNotExist:
            return Response({"detail": "计划不存在"}, status=status.HTTP_404_NOT_FOUND)
        if plan.status != ImprovementPlan.Status.PUBLISHED:
            return Response({"detail": "只能归档已发布的计划"}, status=status.HTTP_400_BAD_REQUEST)
        plan.status = ImprovementPlan.Status.ARCHIVED
        plan.archived_at = timezone.now()
        plan.save(update_fields=["status", "archived_at", "updated_at"])
        return Response(PlanDetailSerializer(plan).data)


class PlanGenerateView(APIView):
    """POST /api/kpi/plans/generate/ — 为指定用户生成 AI 草案。"""
    permission_classes = [FullDjangoModelPermissions]
    queryset = ImprovementPlan.objects.none()

    def post(self, request):
        from django.contrib.auth import get_user_model
        from .plan_generator import generate_action_items
        from .services import KPIService

        User = get_user_model()
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"detail": "缺少 user_id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "用户不存在"}, status=status.HTTP_404_NOT_FOUND)

        period = timezone.now().strftime("%Y-%m")
        if ImprovementPlan.objects.filter(user=target_user, period=period).exists():
            return Response({"detail": "该用户本月已有计划"}, status=status.HTTP_409_CONFLICT)

        today = timezone.now().date()
        month_start = today.replace(day=1)
        svc = KPIService()
        kpi_data = svc.compute_for_user(target_user, month_start, today)

        users = svc._get_target_users()
        team_scores = [svc.compute_for_user(u, month_start, today)["scores"] for u in users]
        dims = ("efficiency", "output", "quality", "capability")
        team_avgs = {}
        if team_scores:
            for d in dims:
                vals = [s.get(d, 0) for s in team_scores]
                team_avgs[d] = round(sum(vals) / len(vals), 1)

        items_data = generate_action_items(
            kpi_data["scores"], kpi_data["issue_metrics"],
            kpi_data["commit_metrics"], team_avgs,
        )

        plan = ImprovementPlan.objects.create(
            user=target_user, period=period,
            status=ImprovementPlan.Status.DRAFT,
            source_kpi_scores=kpi_data["scores"],
        )
        for i, item_data in enumerate(items_data):
            ActionItem.objects.create(plan=plan, sort_order=i, **item_data)

        return Response(PlanDetailSerializer(plan).data, status=status.HTTP_201_CREATED)


class PlanEditView(APIView):
    """PUT /api/kpi/plans/{id}/edit/ — 管理员编辑计划。"""
    permission_classes = [FullDjangoModelPermissions]
    queryset = ImprovementPlan.objects.none()

    def put(self, request, pk):
        try:
            plan = ImprovementPlan.objects.get(pk=pk)
        except ImprovementPlan.DoesNotExist:
            return Response({"detail": "计划不存在"}, status=status.HTTP_404_NOT_FOUND)

        items_data = request.data.get("action_items", [])
        existing_ids = set(str(item.id) for item in plan.action_items.all())
        incoming_ids = set(str(item["id"]) for item in items_data if item.get("id"))

        to_delete = existing_ids - incoming_ids
        if to_delete:
            ActionItem.objects.filter(id__in=to_delete, plan=plan).delete()

        for i, item_data in enumerate(items_data):
            item_id = item_data.get("id")
            defaults = {
                "title": item_data.get("title", ""),
                "description": item_data.get("description", ""),
                "measurable_target": item_data.get("measurable_target", ""),
                "points": item_data.get("points", 10),
                "priority": item_data.get("priority", "medium"),
                "dimension": item_data.get("dimension", "general"),
                "sort_order": i,
            }
            if item_id and str(item_id) in existing_ids:
                ActionItem.objects.filter(id=item_id, plan=plan).update(**defaults)
            else:
                ActionItem.objects.create(plan=plan, source=ActionItem.Source.MANAGER, **defaults)

        plan.refresh_from_db()
        return Response(PlanDetailSerializer(plan).data)


class ActionItemStatusView(APIView):
    """POST /api/kpi/action-items/{id}/status/ — 员工更新状态。"""
    permission_classes = [IsAuthenticated]

    EMPLOYEE_TRANSITIONS = {
        "pending": ["in_progress"],
        "in_progress": ["submitted"],
    }

    def post(self, request, pk):
        try:
            item = ActionItem.objects.select_related("plan").get(pk=pk)
        except ActionItem.DoesNotExist:
            return Response({"detail": "行动项不存在"}, status=status.HTTP_404_NOT_FOUND)
        if item.plan.user != request.user:
            return Response({"detail": "只能操作自己的行动项"}, status=status.HTTP_403_FORBIDDEN)
        new_status = request.data.get("status")
        allowed = self.EMPLOYEE_TRANSITIONS.get(item.status, [])
        if new_status not in allowed:
            return Response(
                {"detail": f"不允许从 {item.status} 变更为 {new_status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        item.status = new_status
        item.save(update_fields=["status", "updated_at"])
        return Response(ActionItemSerializer(item).data)


class ActionItemVerifyView(APIView):
    """POST /api/kpi/action-items/{id}/verify/ — 管理员验收。"""
    permission_classes = [FullDjangoModelPermissions]
    queryset = ImprovementPlan.objects.none()

    def post(self, request, pk):
        try:
            item = ActionItem.objects.get(pk=pk)
        except ActionItem.DoesNotExist:
            return Response({"detail": "行动项不存在"}, status=status.HTTP_404_NOT_FOUND)
        new_status = request.data.get("status")
        if new_status not in ("verified", "not_achieved"):
            return Response({"detail": "状态必须为 verified 或 not_achieved"}, status=status.HTTP_400_BAD_REQUEST)
        if new_status == "verified":
            qf = request.data.get("quality_factor")
            if qf is None:
                return Response({"detail": "验收需要提供 quality_factor"}, status=status.HTTP_400_BAD_REQUEST)
            item.quality_factor = qf
        item.status = new_status
        item.save(update_fields=["status", "quality_factor", "updated_at"])
        return Response(ActionItemSerializer(item).data)


class ActionItemCommentListView(APIView):
    """GET/POST /api/kpi/action-items/{id}/comments/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        comments = ActionItemComment.objects.filter(action_item_id=pk).select_related("author")
        serializer = ActionItemCommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        try:
            item = ActionItem.objects.select_related("plan").get(pk=pk)
        except ActionItem.DoesNotExist:
            return Response({"detail": "行动项不存在"}, status=status.HTTP_404_NOT_FOUND)
        if item.plan.user != request.user and not request.user.has_perm("kpi.change_improvementplan"):
            return Response({"detail": "无权评论"}, status=status.HTTP_403_FORBIDDEN)
        content = request.data.get("content", "").strip()
        if not content:
            return Response({"detail": "评论内容不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        attachment_url = ""
        attachment_key = ""
        if "attachment" in request.FILES:
            attachment_url, attachment_key = upload_image(request.FILES["attachment"])
        comment = ActionItemComment.objects.create(
            action_item=item, author=request.user, content=content,
            attachment_url=attachment_url, attachment_key=attachment_key,
        )
        return Response(ActionItemCommentSerializer(comment).data, status=status.HTTP_201_CREATED)
