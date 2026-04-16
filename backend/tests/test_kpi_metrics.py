import pytest
from django.utils import timezone
from apps.kpi.models import KPISnapshot
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestKPISnapshotModel:
    def test_create_snapshot(self):
        user = UserFactory()
        snap = KPISnapshot.objects.create(
            user=user,
            period_start="2026-04-01",
            period_end="2026-04-15",
            issue_metrics={"assigned_count": 10, "resolved_count": 8},
            commit_metrics={"total_commits": 50},
            scores={"efficiency": 80, "output": 75, "quality": 90, "capability": 70, "growth": 60, "overall": 77},
            rankings={"overall_rank": 2, "total_developers": 5},
            suggestions={"profile": "均衡发展型"},
            computed_at=timezone.now(),
        )
        assert snap.pk is not None
        assert str(snap) == f"{user} | 2026-04-01 ~ 2026-04-15"

    def test_unique_constraint(self):
        user = UserFactory()
        KPISnapshot.objects.create(
            user=user, period_start="2026-04-01", period_end="2026-04-15",
            computed_at=timezone.now(),
        )
        with pytest.raises(Exception):
            KPISnapshot.objects.create(
                user=user, period_start="2026-04-01", period_end="2026-04-15",
                computed_at=timezone.now(),
            )
