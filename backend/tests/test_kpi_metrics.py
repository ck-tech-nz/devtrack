import pytest
from datetime import date, timedelta
from django.contrib.auth.models import Group
from django.utils import timezone
from apps.kpi.models import KPISnapshot
from apps.kpi.metrics import compute_issue_metrics, compute_commit_metrics
from apps.kpi.services import KPIService
from tests.factories import (
    UserFactory,
    ProjectFactory,
    IssueFactory,
    ActivityFactory,
    RepoFactory,
    CommitFactory,
    GitAuthorAliasFactory,
)

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


# ---------------------------------------------------------------------------
# Issue Metrics Tests
# ---------------------------------------------------------------------------


class TestIssueMetrics:
    def test_basic_issue_metrics(self):
        """3 个已解决 + 1 个未解决，验证计数、比率、平均小时、优先级拆分。"""
        user = UserFactory()
        project = ProjectFactory()
        base = timezone.make_aware(timezone.datetime(2026, 4, 5, 10, 0))

        # 3 个已解决（P0, P1, P2），各花 24h
        for i, prio in enumerate(["P0", "P1", "P2"]):
            issue = IssueFactory(
                project=project,
                assignee=user,
                priority=prio,
                status="已解决",
                created_by=user,
            )
            # 手动设置 created_at / resolved_at 确保精确
            issue.created_at = base + timedelta(days=i)
            issue.resolved_at = base + timedelta(days=i, hours=24)
            issue.save(update_fields=["created_at", "resolved_at"])
            # 给每个 issue 加一条 Activity
            ActivityFactory(user=user, issue=issue, action="comment")

        # 1 个未解决（P3）
        unresolved = IssueFactory(
            project=project,
            assignee=user,
            priority="P3",
            status="进行中",
            created_by=user,
        )
        unresolved.created_at = base + timedelta(days=3)
        unresolved.save(update_fields=["created_at"])

        result = compute_issue_metrics(user, date(2026, 4, 1), date(2026, 4, 30))

        assert result["assigned_count"] == 4
        assert result["resolved_count"] == 3
        assert result["resolution_rate"] == 0.75
        assert result["avg_resolution_hours"] == 24.0

        # 优先级拆分
        pb = result["priority_breakdown"]
        assert pb["P0"]["assigned"] == 1
        assert pb["P0"]["resolved"] == 1
        assert pb["P0"]["avg_hours"] == 24.0
        assert pb["P3"]["assigned"] == 1
        assert pb["P3"]["resolved"] == 0

        # weighted_issue_value > 0（每个 resolved 都有 24h 和 1 activity）
        assert result["weighted_issue_value"] > 0

        # daily / weekly averages
        assert result["daily_resolved_avg"] > 0
        assert result["weekly_resolved_avg"] > 0

    def test_issue_metrics_empty(self):
        """没有任何 Issue 时返回全零。"""
        user = UserFactory()
        result = compute_issue_metrics(user, date(2026, 4, 1), date(2026, 4, 30))

        assert result["assigned_count"] == 0
        assert result["resolved_count"] == 0
        assert result["resolution_rate"] == 0
        assert result["avg_resolution_hours"] == 0
        assert result["weighted_issue_value"] == 0
        assert result["as_helper_count"] == 0
        for prio in ("P0", "P1", "P2", "P3"):
            assert result["priority_breakdown"][prio]["assigned"] == 0

    def test_helper_count(self):
        """验证 as_helper_count: 用户作为协助人但不是负责人。"""
        user = UserFactory()
        assignee = UserFactory()
        project = ProjectFactory()
        base = timezone.make_aware(timezone.datetime(2026, 4, 5, 10, 0))

        # Issue 1: user 是协助人，assignee 是别人
        issue1 = IssueFactory(
            project=project,
            assignee=assignee,
            priority="P1",
            status="进行中",
            created_by=assignee,
        )
        issue1.created_at = base
        issue1.save(update_fields=["created_at"])
        issue1.helpers.add(user)

        # Issue 2: user 既是 assignee 又是 helper —— 不应计入 as_helper_count
        issue2 = IssueFactory(
            project=project,
            assignee=user,
            priority="P2",
            status="待处理",
            created_by=assignee,
        )
        issue2.created_at = base + timedelta(days=1)
        issue2.save(update_fields=["created_at"])
        issue2.helpers.add(user)

        result = compute_issue_metrics(user, date(2026, 4, 1), date(2026, 4, 30))
        assert result["as_helper_count"] == 1


# ---------------------------------------------------------------------------
# Commit Metrics Tests
# ---------------------------------------------------------------------------


class TestCommitMetrics:
    def test_basic_commit_metrics(self):
        """5 个 feat + 1 个 fix（同文件 72h 内），验证全部字段。"""
        user = UserFactory()
        repo = RepoFactory(clone_status="cloned")
        email = "dev@example.com"
        GitAuthorAliasFactory(repo=repo, user=user, author_email=email)

        base = timezone.make_aware(timezone.datetime(2026, 4, 5, 10, 0))
        shared_file = "src/app.py"

        # 5 个 feat commits
        for i in range(5):
            CommitFactory(
                repo=repo,
                author_email=email,
                author_name=user.name,
                message=f"feat: add feature {i}",
                date=base + timedelta(hours=i * 2),
                additions=30 + i * 10,
                deletions=5 + i,
                files_changed=[shared_file, f"src/module_{i}.ts"],
            )

        # 1 个 fix commit（同一文件，48h 后 — 仍在 72h 窗口内）
        CommitFactory(
            repo=repo,
            author_email=email,
            author_name=user.name,
            message="fix: resolve bug in app",
            date=base + timedelta(hours=48),
            additions=5,
            deletions=3,
            files_changed=[shared_file],
        )

        result = compute_commit_metrics(user, date(2026, 4, 1), date(2026, 4, 30))

        assert result["total_commits"] == 6
        assert result["additions"] > 0
        assert result["deletions"] > 0
        assert result["lines_changed"] == result["additions"] + result["deletions"]

        # Commit 大小分布
        dist = result["commit_size_distribution"]
        assert dist["small"] + dist["medium"] + dist["large"] == 6

        # 文件类型广度 — py + ts = 2
        assert result["file_type_breadth"] >= 2

        # 工作节奏
        assert len(result["work_rhythm"]["by_hour"]) == 24
        assert len(result["work_rhythm"]["by_weekday"]) == 7

        # Conventional commit ratio
        assert result["conventional_ratio"] == 1.0

        # commit_type_distribution
        assert result["commit_type_distribution"]["feat"] == 5
        assert result["commit_type_distribution"]["fix"] == 1

        # refactor_ratio — 无 refactor
        assert result["refactor_ratio"] == 0

        # self_introduced_bug_rate > 0（feat commit 48h 后同文件有 fix）
        assert result["self_introduced_bug_rate"] > 0

        # avg_commit_size
        assert result["avg_commit_size"] > 0

        # repo_coverage
        assert len(result["repo_coverage"]) == 1
        assert result["repo_coverage"][0]["repo_id"] == repo.id
        assert result["repo_coverage"][0]["commits"] == 6

    def test_commit_metrics_no_commits(self):
        """无 commit 返回空指标。"""
        user = UserFactory()

        result = compute_commit_metrics(user, date(2026, 4, 1), date(2026, 4, 30))

        assert result["total_commits"] == 0
        assert result["additions"] == 0
        assert result["deletions"] == 0
        assert result["lines_changed"] == 0
        assert result["self_introduced_bug_rate"] == 0
        assert result["churn_rate"] == 0
        assert result["commit_size_distribution"] == {"small": 0, "medium": 0, "large": 0}
        assert result["avg_commit_size"] == 0
        assert result["file_type_breadth"] == 0
        assert result["work_rhythm"]["by_hour"] == [0] * 24
        assert result["work_rhythm"]["by_weekday"] == [0] * 7
        assert result["refactor_ratio"] == 0
        assert result["commit_type_distribution"] == {}
        assert result["conventional_ratio"] == 0
        assert result["repo_coverage"] == []


# ---------------------------------------------------------------------------
# KPI Service Tests
# ---------------------------------------------------------------------------


class TestKPIService:
    def test_refresh_computes_snapshots(self, site_settings):
        group, _ = Group.objects.get_or_create(name="开发者")
        user1 = UserFactory()
        user1.groups.add(group)
        user2 = UserFactory()
        user2.groups.add(group)
        project = ProjectFactory()

        for u in (user1, user2):
            IssueFactory(
                project=project, assignee=u, priority="P1",
                status="已解决", created_by=UserFactory(),
                resolved_at=timezone.now(), created_at=timezone.now() - timedelta(hours=10),
            )

        start = date(2026, 1, 1)
        end = date(2026, 12, 31)
        result = KPIService().refresh(start, end, role="开发者")

        assert result["user_count"] == 2
        assert KPISnapshot.objects.count() == 2

        snap = KPISnapshot.objects.filter(user=user1).first()
        assert snap is not None
        assert snap.scores["overall"] >= 0
        assert snap.rankings["total_developers"] == 2
        assert snap.suggestions["profile"]

    def test_refresh_updates_existing_snapshot(self, site_settings):
        group, _ = Group.objects.get_or_create(name="开发者")
        user = UserFactory()
        user.groups.add(group)

        start = date(2026, 4, 1)
        end = date(2026, 4, 15)
        KPIService().refresh(start, end, role="开发者")
        assert KPISnapshot.objects.count() == 1

        KPIService().refresh(start, end, role="开发者")
        assert KPISnapshot.objects.count() == 1
