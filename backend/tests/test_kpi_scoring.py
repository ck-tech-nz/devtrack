import pytest
from apps.kpi.scoring import compute_scores, compute_rankings

pytestmark = pytest.mark.django_db

DIMENSIONS = ("efficiency", "output", "quality", "capability", "growth", "overall")


def _sample_issue_metrics(**overrides) -> dict:
    """返回一组合理的 issue_metrics 默认值，可通过 overrides 覆盖。"""
    base = {
        "assigned_count": 10,
        "resolved_count": 8,
        "resolution_rate": 0.8,
        "avg_resolution_hours": 24.0,
        "daily_resolved_avg": 0.5,
        "weekly_resolved_avg": 3.5,
        "priority_breakdown": {
            "P0": {"assigned": 2, "resolved": 2, "avg_hours": 12.0},
            "P1": {"assigned": 3, "resolved": 3, "avg_hours": 18.0},
            "P2": {"assigned": 3, "resolved": 2, "avg_hours": 36.0},
            "P3": {"assigned": 2, "resolved": 1, "avg_hours": 48.0},
        },
        "weighted_issue_value": 80.0,
        "as_helper_count": 3,
    }
    base.update(overrides)
    return base


def _sample_commit_metrics(**overrides) -> dict:
    """返回一组合理的 commit_metrics 默认值，可通过 overrides 覆盖。"""
    base = {
        "total_commits": 40,
        "additions": 1200,
        "deletions": 300,
        "lines_changed": 1500,
        "self_introduced_bug_rate": 0.1,
        "churn_rate": 0.2,
        "commit_size_distribution": {"small": 15, "medium": 20, "large": 5},
        "avg_commit_size": 75.0,
        "file_type_breadth": 5,
        "work_rhythm": {"by_hour": [0] * 24, "by_weekday": [0] * 7},
        "refactor_ratio": 0.05,
        "commit_type_distribution": {"feat": 25, "fix": 10, "refactor": 2, "chore": 3},
        "conventional_ratio": 0.85,
        "repo_coverage": [
            {"repo_id": 1, "repo_name": "backend", "commits": 30},
            {"repo_id": 2, "repo_name": "frontend", "commits": 10},
        ],
    }
    base.update(overrides)
    return base


class TestComputeScoresBasic:
    """验证 compute_scores 返回所有维度且分数在 0-100 范围内。"""

    def test_all_dimensions_present_and_in_range(self):
        im = _sample_issue_metrics()
        cm = _sample_commit_metrics()

        scores = compute_scores(im, cm)

        for dim in DIMENSIONS:
            assert dim in scores, f"缺少维度: {dim}"
            assert isinstance(scores[dim], int), f"{dim} 应为整数"
            assert 0 <= scores[dim] <= 100, f"{dim}={scores[dim]} 超出范围"

    def test_zero_metrics_produce_valid_scores(self):
        """全零指标也应返回合法评分（不崩溃，全部 0-100）。"""
        im = {
            "assigned_count": 0,
            "resolved_count": 0,
            "resolution_rate": 0,
            "avg_resolution_hours": 0,
            "daily_resolved_avg": 0,
            "weekly_resolved_avg": 0,
            "priority_breakdown": {
                prio: {"assigned": 0, "resolved": 0, "avg_hours": 0}
                for prio in ("P0", "P1", "P2", "P3")
            },
            "weighted_issue_value": 0,
            "as_helper_count": 0,
        }
        cm = {
            "total_commits": 0,
            "additions": 0,
            "deletions": 0,
            "lines_changed": 0,
            "self_introduced_bug_rate": 0,
            "churn_rate": 0,
            "commit_size_distribution": {"small": 0, "medium": 0, "large": 0},
            "avg_commit_size": 0,
            "file_type_breadth": 0,
            "work_rhythm": {"by_hour": [0] * 24, "by_weekday": [0] * 7},
            "refactor_ratio": 0,
            "commit_type_distribution": {},
            "conventional_ratio": 0,
            "repo_coverage": [],
        }

        scores = compute_scores(im, cm)

        for dim in DIMENSIONS:
            assert 0 <= scores[dim] <= 100

    def test_high_metrics_produce_high_scores(self):
        """高指标应产生较高的 efficiency/output 分数。"""
        im = _sample_issue_metrics(
            daily_resolved_avg=3.0,
            avg_resolution_hours=4.0,
            resolved_count=30,
            weighted_issue_value=200.0,
            as_helper_count=10,
        )
        im["priority_breakdown"]["P0"]["avg_hours"] = 2.0
        im["priority_breakdown"]["P1"]["avg_hours"] = 3.0

        cm = _sample_commit_metrics(
            total_commits=100,
            conventional_ratio=1.0,
            self_introduced_bug_rate=0.0,
            churn_rate=0.0,
            avg_commit_size=100.0,
            file_type_breadth=8,
        )
        cm["repo_coverage"] = [{"repo_id": i, "repo_name": f"r{i}", "commits": 20} for i in range(5)]

        scores = compute_scores(im, cm)

        assert scores["efficiency"] >= 70
        assert scores["output"] >= 70
        assert scores["quality"] >= 70


class TestGrowthWithPrevious:
    """验证当提供 prev_scores 时 growth 不再固定为 50。"""

    def test_growth_differs_from_50_with_prev(self):
        im = _sample_issue_metrics()
        cm = _sample_commit_metrics()

        # 无历史 -> growth 应为 50
        scores_no_prev = compute_scores(im, cm, prev_scores=None)
        assert scores_no_prev["growth"] == 50

        # 有历史且当前分数明显高于历史 -> growth > 50
        low_prev = {"efficiency": 10, "output": 10, "quality": 10, "capability": 10}
        scores_growth_up = compute_scores(im, cm, prev_scores=low_prev)
        assert scores_growth_up["growth"] != 50
        assert scores_growth_up["growth"] > 50

        # 有历史且当前分数明显低于历史 -> growth < 50
        high_prev = {"efficiency": 95, "output": 95, "quality": 95, "capability": 95}
        scores_growth_down = compute_scores(im, cm, prev_scores=high_prev)
        assert scores_growth_down["growth"] < 50

    def test_growth_none_prev_scores_treated_as_no_history(self):
        im = _sample_issue_metrics()
        cm = _sample_commit_metrics()

        scores = compute_scores(im, cm, prev_scores=None)
        assert scores["growth"] == 50

    def test_growth_empty_prev_scores_treated_as_no_history(self):
        im = _sample_issue_metrics()
        cm = _sample_commit_metrics()

        scores = compute_scores(im, cm, prev_scores={})
        assert scores["growth"] == 50


class TestComputeRankings:
    """3 个用户，验证排名和百分位的正确性。"""

    def test_three_users_ranks_and_percentiles(self):
        all_scores = [
            {"user_id": 1, "scores": {"efficiency": 90, "output": 80, "quality": 70, "capability": 60, "growth": 50, "overall": 75}},
            {"user_id": 2, "scores": {"efficiency": 60, "output": 50, "quality": 80, "capability": 70, "growth": 60, "overall": 62}},
            {"user_id": 3, "scores": {"efficiency": 30, "output": 40, "quality": 90, "capability": 80, "growth": 70, "overall": 55}},
        ]

        rankings = compute_rankings(all_scores)

        assert len(rankings) == 3

        for uid in (1, 2, 3):
            r = rankings[uid]
            assert r["total_developers"] == 3
            assert "overall_rank" in r
            assert "overall_percentile" in r
            assert "efficiency_percentile" in r

        # overall_rank: user1 (75) > user2 (62) > user3 (55)
        assert rankings[1]["overall_rank"] == 1
        assert rankings[2]["overall_rank"] == 2
        assert rankings[3]["overall_rank"] == 3

        # efficiency_rank: user1 (90) > user2 (60) > user3 (30)
        assert rankings[1]["efficiency_rank"] == 1
        assert rankings[3]["efficiency_rank"] == 3

        # quality_rank: user3 (90) > user2 (80) > user1 (70)
        assert rankings[3]["quality_rank"] == 1
        assert rankings[1]["quality_rank"] == 3

        # percentile: count_below / (n-1) * 100
        # user1 efficiency=90: count_below=2, percentile = 2/2*100 = 100
        assert rankings[1]["efficiency_percentile"] == 100
        # user3 efficiency=30: count_below=0, percentile = 0/2*100 = 0
        assert rankings[3]["efficiency_percentile"] == 0
        # user2 efficiency=60: count_below=1, percentile = 1/2*100 = 50
        assert rankings[2]["efficiency_percentile"] == 50

    def test_single_developer_gets_50_percentile(self):
        """单个开发者百分位应为 50。"""
        all_scores = [
            {"user_id": 42, "scores": {"efficiency": 80, "output": 70, "quality": 60, "capability": 50, "growth": 40, "overall": 60}},
        ]

        rankings = compute_rankings(all_scores)

        assert rankings[42]["total_developers"] == 1
        assert rankings[42]["overall_percentile"] == 50
        assert rankings[42]["efficiency_percentile"] == 50
        assert rankings[42]["overall_rank"] == 1

    def test_empty_input_returns_empty(self):
        assert compute_rankings([]) == {}
