import pytest
from django.utils import timezone
from tests.factories import UserFactory, ImprovementPlanFactory, ActionItemFactory

pytestmark = pytest.mark.django_db


class TestImprovementPlan:
    def test_create_plan(self):
        plan = ImprovementPlanFactory()
        assert plan.status == "draft"
        assert plan.period
        assert plan.user is not None

    def test_unique_user_period(self):
        plan = ImprovementPlanFactory(period="2026-04")
        with pytest.raises(Exception):
            ImprovementPlanFactory(user=plan.user, period="2026-04")

    def test_plan_str(self):
        plan = ImprovementPlanFactory()
        assert plan.user.name in str(plan)
        assert plan.period in str(plan)


class TestActionItem:
    def test_create_action_item(self):
        item = ActionItemFactory()
        assert item.status == "pending"
        assert item.points > 0
        assert item.plan is not None

    def test_earned_points_verified(self):
        item = ActionItemFactory(status="verified", points=100, quality_factor=1.2)
        assert item.earned_points == 120

    def test_earned_points_not_verified(self):
        item = ActionItemFactory(status="pending", points=100)
        assert item.earned_points == 0

    def test_status_choices(self):
        for status in ("pending", "in_progress", "submitted", "verified", "not_achieved"):
            item = ActionItemFactory(status=status)
            assert item.status == status
