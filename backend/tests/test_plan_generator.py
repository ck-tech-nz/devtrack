import pytest
from tests.factories import UserFactory
from apps.kpi.plan_generator import generate_action_items

pytestmark = pytest.mark.django_db


def _sample_scores(**overrides):
    base = {"efficiency": 70, "output": 75, "quality": 80, "capability": 65, "growth": 50, "overall": 72}
    base.update(overrides)
    return base


def _sample_issue_metrics(**overrides):
    base = {
        "assigned_count": 10, "resolved_count": 8, "resolution_rate": 0.8,
        "avg_resolution_hours": 12.0, "daily_resolved_avg": 1.5,
        "weighted_issue_value": 30, "as_helper_count": 0,
        "priority_breakdown": {"P0": {"assigned": 2, "resolved": 1, "avg_hours": 8}},
    }
    base.update(overrides)
    return base


def _sample_commit_metrics(**overrides):
    base = {
        "total_commits": 50, "additions": 3000, "deletions": 1000,
        "self_introduced_bug_rate": 0.05, "churn_rate": 0.1,
        "conventional_ratio": 0.7, "avg_commit_size": 100,
        "repo_coverage": [{"repo_name": "repo1"}],
        "file_type_breadth": 5,
    }
    base.update(overrides)
    return base


class TestGenerateActionItems:
    def test_generates_items_for_low_efficiency(self):
        scores = _sample_scores(efficiency=40)
        team_avgs = {"efficiency": 70, "output": 70, "quality": 70, "capability": 70}
        items = generate_action_items(scores, _sample_issue_metrics(), _sample_commit_metrics(), team_avgs)
        dims = [i["dimension"] for i in items]
        assert "efficiency" in dims

    def test_generates_items_for_high_bug_rate(self):
        cm = _sample_commit_metrics(self_introduced_bug_rate=0.15)
        items = generate_action_items(_sample_scores(), _sample_issue_metrics(), cm, {})
        dims = [i["dimension"] for i in items]
        assert "quality" in dims

    def test_max_8_items(self):
        scores = _sample_scores(efficiency=10, output=10, quality=10, capability=10)
        team_avgs = {"efficiency": 70, "output": 70, "quality": 70, "capability": 70}
        cm = _sample_commit_metrics(
            self_introduced_bug_rate=0.2, churn_rate=0.3,
            conventional_ratio=0.3, avg_commit_size=400,
        )
        im = _sample_issue_metrics(as_helper_count=0)
        items = generate_action_items(scores, im, cm, team_avgs)
        assert len(items) <= 8

    def test_returns_structured_items(self):
        items = generate_action_items(
            _sample_scores(efficiency=30),
            _sample_issue_metrics(),
            _sample_commit_metrics(),
            {"efficiency": 70},
        )
        assert len(items) > 0
        item = items[0]
        assert "title" in item
        assert "description" in item
        assert "measurable_target" in item
        assert "points" in item
        assert "priority" in item
        assert "dimension" in item

    def test_no_items_when_all_good(self):
        scores = _sample_scores(efficiency=90, output=90, quality=90, capability=90)
        cm = _sample_commit_metrics(
            self_introduced_bug_rate=0.02, churn_rate=0.05,
            conventional_ratio=0.9, avg_commit_size=80,
            repo_coverage=[{"repo_name": "r1"}, {"repo_name": "r2"}, {"repo_name": "r3"}],
        )
        im = _sample_issue_metrics(as_helper_count=5)
        items = generate_action_items(scores, im, cm, {"efficiency": 70, "output": 70})
        assert len(items) == 0
