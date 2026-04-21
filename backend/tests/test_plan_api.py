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
