import pytest
from django.contrib.auth.models import Group, Permission
from django.utils import timezone as tz
from rest_framework.test import APIClient

from tests.factories import UserFactory, KPISnapshotFactory


@pytest.fixture
def kpi_manager_client(api_client):
    """User with all KPISnapshot permissions + issue/user/repo perms."""
    user = UserFactory()
    group, _ = Group.objects.get_or_create(name="KPI管理员")
    group.permissions.set(
        Permission.objects.filter(
            content_type__app_label__in=["kpi", "issues", "users", "repos"]
        )
    )
    user.groups.add(group)
    api_client.force_authenticate(user=user)
    api_client._user = user
    return api_client


@pytest.fixture
def kpi_dev_client(api_client):
    """User with only view_own_kpi permission."""
    user = UserFactory()
    group, _ = Group.objects.get_or_create(name="KPI开发者")
    perm = Permission.objects.get(codename="view_own_kpi")
    group.permissions.add(perm)
    user.groups.add(group)
    api_client.force_authenticate(user=user)
    api_client._user = user
    return api_client


def _create_snapshot(user=None, **kwargs):
    """Helper to create a KPISnapshot with default data."""
    if user:
        kwargs["user"] = user
    return KPISnapshotFactory(**kwargs)


@pytest.mark.django_db
class TestTeamDashboardAPI:
    def test_team_returns_data(self, kpi_manager_client):
        today = tz.now().date()
        period_start = today.replace(day=1)

        snap1 = _create_snapshot(
            period_start=period_start,
            period_end=today,
            scores={"efficiency": 80, "output": 85, "quality": 90, "capability": 75, "growth": 60, "overall": 82},
            rankings={"overall_rank": 1, "total_developers": 2},
        )
        snap2 = _create_snapshot(
            period_start=period_start,
            period_end=today,
            scores={"efficiency": 60, "output": 65, "quality": 70, "capability": 55, "growth": 40, "overall": 62},
            rankings={"overall_rank": 2, "total_developers": 2},
        )

        resp = kpi_manager_client.get("/api/kpi/team/")
        assert resp.status_code == 200
        data = resp.json()
        assert "developers" in data
        assert len(data["developers"]) == 2
        assert data["period_start"] == period_start.isoformat()
        assert data["period_end"] == today.isoformat()

    def test_team_forbidden_for_dev(self, kpi_dev_client):
        resp = kpi_dev_client.get("/api/kpi/team/")
        assert resp.status_code == 403


@pytest.mark.django_db
class TestIndividualKPIAPI:
    def test_user_summary(self, kpi_manager_client):
        today = tz.now().date()
        period_start = today.replace(day=1)

        user = UserFactory()
        snap = _create_snapshot(user=user, period_start=period_start, period_end=today)

        resp = kpi_manager_client.get(f"/api/kpi/users/{user.id}/summary/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == user.id
        assert "scores" in data
        assert "rankings" in data

    def test_dev_can_view_own(self, kpi_dev_client):
        today = tz.now().date()
        period_start = today.replace(day=1)

        user = kpi_dev_client._user
        snap = _create_snapshot(user=user, period_start=period_start, period_end=today)

        resp = kpi_dev_client.get(f"/api/kpi/users/{user.id}/summary/")
        assert resp.status_code == 200

    def test_dev_cannot_view_others(self, kpi_dev_client):
        today = tz.now().date()
        period_start = today.replace(day=1)

        other_user = UserFactory()
        snap = _create_snapshot(user=other_user, period_start=period_start, period_end=today)

        resp = kpi_dev_client.get(f"/api/kpi/users/{other_user.id}/summary/")
        assert resp.status_code == 403

    def test_trends_endpoint(self, kpi_manager_client):
        user = UserFactory()
        today = tz.now().date()

        # Create 3 snapshots with different periods
        for i in range(3):
            month = today.month - 2 + i
            year = today.year
            if month < 1:
                month += 12
                year -= 1
            start = today.replace(year=year, month=month, day=1)
            end = today.replace(year=year, month=month, day=28)
            _create_snapshot(
                user=user,
                period_start=start,
                period_end=end,
                scores={"overall": 60 + i * 5, "efficiency": 70 + i * 2},
            )

        resp = kpi_manager_client.get(f"/api/kpi/users/{user.id}/trends/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        # Should be sorted chronologically (ascending)
        assert data[0]["period_end"] <= data[1]["period_end"]


@pytest.mark.django_db
class TestRefreshAPI:
    def test_refresh_requires_permission(self, kpi_dev_client):
        resp = kpi_dev_client.post("/api/kpi/refresh/")
        assert resp.status_code == 403

    def test_refresh_works_for_manager(self, kpi_manager_client):
        # Create a non-bot active user so refresh has something to compute
        user = UserFactory(is_bot=False, is_active=True)

        resp = kpi_manager_client.post("/api/kpi/refresh/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "computed_at" in data
        assert "user_count" in data


@pytest.mark.django_db
class TestMeAPI:
    def test_me_summary(self, kpi_dev_client):
        today = tz.now().date()
        period_start = today.replace(day=1)

        user = kpi_dev_client._user
        snap = _create_snapshot(user=user, period_start=period_start, period_end=today)

        resp = kpi_dev_client.get("/api/kpi/me/summary/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == user.id
        assert "scores" in data
