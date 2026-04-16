from apps.kpi.suggestions import generate_suggestions


class TestShortcomingsDetected:
    """低分 + 差指标 → 验证短板被正确检测，quality 在维度列表中。"""

    def test_shortcomings_detected(self):
        scores = {
            "efficiency": 50,
            "output": 60,
            "quality": 40,
            "capability": 55,
            "growth": 50,
        }
        issue_metrics = {
            "avg_resolution_hours": 72,
            "resolved_count": 20,
            "priority_breakdown": {
                "P0": {"assigned": 3, "resolved": 1},
                "P1": {"assigned": 5, "resolved": 5},
                "P2": {"assigned": 8, "resolved": 8},
                "P3": {"assigned": 4, "resolved": 6},
            },
        }
        commit_metrics = {
            "self_introduced_bug_rate": 0.25,
            "churn_rate": 0.35,
            "avg_commit_size": 450,
            "conventional_ratio": 0.3,
            "total_commits": 40,
        }
        team_avgs = {
            "efficiency": 70,
            "output": 65,
            "quality": 70,
            "capability": 60,
            "growth": 55,
        }

        result = generate_suggestions(scores, issue_metrics, commit_metrics, team_avgs, None)
        shortcomings = result["shortcomings"]

        # 至少应检测到多个短板
        assert len(shortcomings) >= 3

        # quality 应该出现在短板维度中
        dims = [s["dimension"] for s in shortcomings]
        assert "quality" in dims

        # 第一个应该是 high severity（self_introduced_bug_rate > 0.1）
        assert shortcomings[0]["severity"] == "high"

        # 验证各条消息都是字符串且非空
        for s in shortcomings:
            assert isinstance(s["message"], str)
            assert len(s["message"]) > 0
            assert s["severity"] in ("high", "medium", "low")


class TestTrendSuggestions:
    """prev_scores efficiency=60, current=80 → 验证 "up" 趋势被检测到。"""

    def test_trend_suggestions(self):
        scores = {
            "efficiency": 80,
            "output": 70,
            "quality": 75,
            "capability": 65,
            "growth": 60,
        }
        prev_scores = {
            "efficiency": 60,
            "output": 70,
            "quality": 75,
            "capability": 65,
            "growth": 55,
        }
        issue_metrics = {
            "avg_resolution_hours": 12,
            "resolved_count": 10,
            "priority_breakdown": {},
        }
        commit_metrics = {
            "self_introduced_bug_rate": 0.05,
            "churn_rate": 0.1,
            "avg_commit_size": 80,
            "conventional_ratio": 0.9,
            "total_commits": 30,
        }

        result = generate_suggestions(scores, issue_metrics, commit_metrics, None, prev_scores)
        trends = result["trends"]

        # efficiency 从 60 → 80，变化 33.3%，应为 "up"
        eff_trends = [t for t in trends if t["dimension"] == "efficiency"]
        assert len(eff_trends) == 1
        assert eff_trends[0]["direction"] == "up"
        assert eff_trends[0]["change_pct"] > 10

        # output 和 quality 没变化，不应出现
        unchanged_dims = [t["dimension"] for t in trends]
        assert "output" not in unchanged_dims
        assert "quality" not in unchanged_dims

    def test_no_trends_without_prev_scores(self):
        """没有历史数据时不产出趋势。"""
        scores = {"efficiency": 80, "output": 70, "quality": 75, "capability": 65, "growth": 60}
        result = generate_suggestions(scores, {}, {}, None, None)
        assert result["trends"] == []


class TestBalancedProfile:
    """所有分数在 10 分以内 → 验证画像包含 "均衡"。"""

    def test_balanced_profile(self):
        scores = {
            "efficiency": 72,
            "output": 75,
            "quality": 74,
            "capability": 70,
            "growth": 73,
        }
        issue_metrics = {
            "avg_resolution_hours": 20,
            "resolved_count": 15,
            "priority_breakdown": {},
        }
        commit_metrics = {
            "self_introduced_bug_rate": 0.05,
            "churn_rate": 0.1,
            "avg_commit_size": 100,
            "conventional_ratio": 0.8,
            "total_commits": 25,
        }

        result = generate_suggestions(scores, issue_metrics, commit_metrics, None, None)
        assert "均衡" in result["profile"]
        assert "稳定" in result["profile"]

    def test_unbalanced_profile_uses_profiles_dict(self):
        """非均衡时使用 PROFILES 查找画像。"""
        scores = {
            "efficiency": 90,
            "output": 60,
            "quality": 50,
            "capability": 70,
            "growth": 65,
        }
        result = generate_suggestions(scores, {}, {}, None, None)
        # highest=efficiency, lowest=quality → "快速响应型，质量有提升空间"
        assert "快速响应型" in result["profile"]
        assert "质量" in result["profile"]
