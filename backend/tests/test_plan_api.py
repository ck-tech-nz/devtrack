import pytest
from django.utils import timezone
from tests.factories import (
    UserFactory, ImprovementPlanFactory, ActionItemFactory,
    ActionItemCommentFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def manager_client(api_client):
    from django.contrib.auth.models import Group, Permission
    user = UserFactory()
    group, _ = Group.objects.get_or_create(name="管理员")
    group.permissions.set(
        Permission.objects.filter(content_type__app_label__in=["kpi", "ai"])
    )
    user.groups.add(group)
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.fixture
def employee_client(api_client):
    from django.contrib.auth.models import Group, Permission
    user = UserFactory()
    group, _ = Group.objects.get_or_create(name="开发者")
    group.permissions.set(
        Permission.objects.filter(codename__in=["view_own_plan", "view_own_kpi"])
    )
    user.groups.add(group)
    api_client.force_authenticate(user=user)
    return api_client, user


class TestPlanListAPI:
    def test_manager_sees_all_plans(self, manager_client):
        client, _ = manager_client
        ImprovementPlanFactory(period="2026-04")
        ImprovementPlanFactory(period="2026-04")
        resp = client.get("/api/kpi/plans/?period=2026-04")
        assert resp.status_code == 200
        assert len(resp.data) == 2

    def test_employee_cannot_list_all(self, employee_client):
        client, _ = employee_client
        resp = client.get("/api/kpi/plans/")
        assert resp.status_code == 403


class TestMyPlanAPI:
    def test_employee_sees_own_published_plan(self, employee_client):
        client, user = employee_client
        plan = ImprovementPlanFactory(user=user, status="published", period=timezone.now().strftime("%Y-%m"))
        ActionItemFactory(plan=plan, title="提高效率")
        resp = client.get("/api/kpi/plans/me/")
        assert resp.status_code == 200
        assert resp.data["current"] is not None
        assert resp.data["current"]["period"] == timezone.now().strftime("%Y-%m")

    def test_employee_cannot_see_draft(self, employee_client):
        client, user = employee_client
        ImprovementPlanFactory(user=user, status="draft", period=timezone.now().strftime("%Y-%m"))
        resp = client.get("/api/kpi/plans/me/")
        assert resp.data["current"] is None


class TestPlanDetailAPI:
    def test_manager_sees_plan_detail(self, manager_client):
        client, _ = manager_client
        plan = ImprovementPlanFactory()
        ActionItemFactory(plan=plan)
        resp = client.get(f"/api/kpi/plans/{plan.id}/")
        assert resp.status_code == 200
        assert len(resp.data["action_items"]) == 1


class TestPlanPublishAPI:
    def test_publish_plan(self, manager_client):
        client, manager = manager_client
        plan = ImprovementPlanFactory(status="draft")
        resp = client.post(f"/api/kpi/plans/{plan.id}/publish/")
        assert resp.status_code == 200
        plan.refresh_from_db()
        assert plan.status == "published"
        assert plan.reviewed_by == manager
        assert plan.published_at is not None


class TestPlanArchiveAPI:
    def test_archive_plan(self, manager_client):
        client, _ = manager_client
        plan = ImprovementPlanFactory(status="published")
        resp = client.post(f"/api/kpi/plans/{plan.id}/archive/")
        assert resp.status_code == 200
        plan.refresh_from_db()
        assert plan.status == "archived"


class TestActionItemStatusAPI:
    def test_employee_updates_own_item_status(self, employee_client):
        client, user = employee_client
        plan = ImprovementPlanFactory(user=user, status="published")
        item = ActionItemFactory(plan=plan, status="pending")
        resp = client.post(
            f"/api/kpi/action-items/{item.id}/status/",
            {"status": "in_progress"}, format="json"
        )
        assert resp.status_code == 200
        item.refresh_from_db()
        assert item.status == "in_progress"

    def test_employee_cannot_verify(self, employee_client):
        client, user = employee_client
        plan = ImprovementPlanFactory(user=user, status="published")
        item = ActionItemFactory(plan=plan, status="submitted")
        resp = client.post(
            f"/api/kpi/action-items/{item.id}/status/",
            {"status": "verified"}, format="json"
        )
        assert resp.status_code == 400


class TestActionItemVerifyAPI:
    def test_manager_verifies_item(self, manager_client):
        client, _ = manager_client
        item = ActionItemFactory(status="submitted", points=100)
        resp = client.post(
            f"/api/kpi/action-items/{item.id}/verify/",
            {"status": "verified", "quality_factor": "1.20"}, format="json"
        )
        assert resp.status_code == 200
        item.refresh_from_db()
        assert item.status == "verified"
        assert float(item.quality_factor) == 1.2


class TestCommentAPI:
    def test_employee_adds_comment(self, employee_client):
        client, user = employee_client
        plan = ImprovementPlanFactory(user=user, status="published")
        item = ActionItemFactory(plan=plan)
        resp = client.post(
            f"/api/kpi/action-items/{item.id}/comments/",
            {"content": "已完成截图见附件"}, format="json"
        )
        assert resp.status_code == 201
        assert item.comments.count() == 1


class TestGeneratePlanAPI:
    def test_manager_generates_plan(self, manager_client):
        client, _ = manager_client
        user = UserFactory(is_active=True, is_bot=False)
        resp = client.post(
            "/api/kpi/plans/generate/",
            {"user_id": user.id}, format="json"
        )
        assert resp.status_code == 201
        assert resp.data["status"] == "draft"


class TestActionItemSerializerFields:
    def test_detail_exposes_review_fields(self, manager_client):
        client, _ = manager_client
        plan = ImprovementPlanFactory()
        ActionItemFactory(
            plan=plan,
            review_dimensions=[{"key": "quality", "label": "完成质量", "weight": 1.0}],
            scores={"quality": 4}, review_comment="不错", status="verified",
        )
        resp = client.get(f"/api/kpi/plans/{plan.id}/")
        item = resp.data["action_items"][0]
        for key in ("scores", "review_comment", "overall_score", "due_date",
                    "review_dimensions", "reviewed_by_name", "reviewed_at"):
            assert key in item
        assert item["overall_score"] == 4.0


class TestTaskDispatchAPI:
    def test_dispatch_creates_published_plan_and_item(self, manager_client):
        client, _ = manager_client
        emp = UserFactory()
        resp = client.post("/api/kpi/tasks/dispatch/", {
            "user_id": emp.id, "title": "读懂订单表设计并写200字理解",
            "due_date": "2026-06-30", "priority": "high",
        }, format="json")
        assert resp.status_code == 201
        from apps.kpi.models import ImprovementPlan, ActionItem
        plan = ImprovementPlan.objects.get(user=emp, period=timezone.now().strftime("%Y-%m"))
        assert plan.status == "published"
        item = ActionItem.objects.get(id=resp.data["id"])
        assert item.status == "pending"
        assert str(item.due_date) == "2026-06-30"
        assert len(item.review_dimensions) == 4

    def test_dispatch_requires_due_date(self, manager_client):
        client, _ = manager_client
        emp = UserFactory()
        resp = client.post("/api/kpi/tasks/dispatch/", {"user_id": emp.id, "title": "x"}, format="json")
        assert resp.status_code == 400

    def test_dispatch_reuses_and_publishes_current_month_plan(self, manager_client):
        client, _ = manager_client
        emp = UserFactory()
        ImprovementPlanFactory(user=emp, period=timezone.now().strftime("%Y-%m"), status="draft")
        resp = client.post("/api/kpi/tasks/dispatch/", {"user_id": emp.id, "title": "任务A", "due_date": "2026-06-30"}, format="json")
        assert resp.status_code == 201
        from apps.kpi.models import ImprovementPlan
        plans = ImprovementPlan.objects.filter(user=emp, period=timezone.now().strftime("%Y-%m"))
        assert plans.count() == 1
        assert plans.first().status == "published"

    def test_dispatch_custom_dimensions_snapshot(self, manager_client):
        client, _ = manager_client
        emp = UserFactory()
        dims = [{"key": "understanding", "label": "理解深度", "weight": 1.0}]
        resp = client.post("/api/kpi/tasks/dispatch/", {"user_id": emp.id, "title": "x", "due_date": "2026-06-30", "review_dimensions": dims}, format="json")
        from apps.kpi.models import ActionItem
        item = ActionItem.objects.get(id=resp.data["id"])
        assert item.review_dimensions == dims

    def test_employee_cannot_dispatch(self, employee_client):
        client, _ = employee_client
        emp = UserFactory()
        resp = client.post("/api/kpi/tasks/dispatch/", {"user_id": emp.id, "title": "x", "due_date": "2026-06-30"}, format="json")
        assert resp.status_code == 403
