# KPI 分析功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cross-repo developer KPI analysis system with team dashboard and personal profiles, featuring 5-dimension scoring, commit mining, trend tracking, and improvement suggestions.

**Architecture:** New `kpi` Django app with a `KPISnapshot` model for pre-computed metrics. Computation service aggregates Issue and Commit data across all repos per user, calculates 5-dimension scores (efficiency, output, quality, capability, growth), generates suggestions via rule engine, and stores results. Frontend has two layers: team dashboard with rankings table, and personal profile with 4 tabs (issues, commits, trends, suggestions).

**Tech Stack:** Django REST Framework, PostgreSQL JSONField, Nuxt 4 (Vue 3 + TypeScript), Tailwind CSS, Chart.js (via existing Charts* components)

**Spec:** `docs/superpowers/specs/2026-04-16-kpi-analysis-design.md`

---

## File Structure

### Backend — New files (all under `backend/apps/kpi/`)

| File | Responsibility |
|------|----------------|
| `__init__.py` | Empty |
| `apps.py` | Django app config |
| `models.py` | `KPISnapshot` model |
| `metrics.py` | Raw metrics computation (issue + commit aggregation) |
| `scoring.py` | 5-dimension scoring engine + overall score |
| `suggestions.py` | Rule engine for improvement suggestions + capability profile |
| `services.py` | Orchestrator: wires metrics → scoring → suggestions → snapshot storage |
| `serializers.py` | DRF serializers for team/individual endpoints |
| `views.py` | API views for team dashboard, individual KPI, refresh |
| `urls.py` | URL routing |
| `admin.py` | Admin registration |

### Backend — Modified files

| File | Change |
|------|--------|
| `backend/config/settings.py` | Add `"apps.kpi"` to INSTALLED_APPS, add KPI route + permissions to PAGE_PERMS |
| `backend/apps/urls.py` | Add `path("kpi/", include("apps.kpi.urls"))` |
| `backend/tests/factories.py` | Add `KPISnapshotFactory` |

### Backend — Test files

| File | Tests |
|------|-------|
| `backend/tests/test_kpi_metrics.py` | Issue + commit metrics computation |
| `backend/tests/test_kpi_scoring.py` | 5-dimension scoring engine |
| `backend/tests/test_kpi_suggestions.py` | Rule engine for suggestions |
| `backend/tests/test_kpi_api.py` | API endpoints + permissions |

### Frontend — New files

| File | Responsibility |
|------|----------------|
| `frontend/app/pages/app/kpi/index.vue` | Team dashboard (manager view) |
| `frontend/app/pages/app/kpi/[id].vue` | Personal KPI profile (4 tabs) |

### Frontend — Modified files

| File | Change |
|------|--------|
| `frontend/app/composables/useNavigation.ts` | Add `/app/kpi` to `用户管理` GROUP_DEFS paths |

---

## Task 1: Django App Scaffold + Model

**Files:**
- Create: `backend/apps/kpi/__init__.py`
- Create: `backend/apps/kpi/apps.py`
- Create: `backend/apps/kpi/models.py`
- Create: `backend/apps/kpi/admin.py`
- Modify: `backend/config/settings.py:21-46` (INSTALLED_APPS)
- Test: `backend/tests/test_kpi_metrics.py` (model-only test)

- [ ] **Step 1: Create the kpi app directory and files**

```bash
mkdir -p backend/apps/kpi
touch backend/apps/kpi/__init__.py
```

- [ ] **Step 2: Create apps.py**

Create `backend/apps/kpi/apps.py`:

```python
from django.apps import AppConfig


class KpiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.kpi"
    verbose_name = "KPI 分析"
```

- [ ] **Step 3: Create models.py with KPISnapshot**

Create `backend/apps/kpi/models.py`:

```python
import uuid

from django.conf import settings
from django.db import models


class KPISnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kpi_snapshots",
        verbose_name="用户",
    )
    period_start = models.DateField(verbose_name="统计起始日期")
    period_end = models.DateField(verbose_name="统计截止日期")
    issue_metrics = models.JSONField(default=dict, verbose_name="问题指标")
    commit_metrics = models.JSONField(default=dict, verbose_name="Commit 指标")
    scores = models.JSONField(default=dict, verbose_name="评分")
    rankings = models.JSONField(default=dict, verbose_name="排名")
    suggestions = models.JSONField(default=dict, verbose_name="改进建议")
    computed_at = models.DateTimeField(verbose_name="计算时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "KPI 快照"
        verbose_name_plural = "KPI 快照"
        unique_together = ("user", "period_start", "period_end")
        ordering = ["-period_end", "-computed_at"]
        permissions = [
            ("view_own_kpi", "Can view own KPI"),
            ("refresh_kpi", "Can refresh KPI data"),
        ]

    def __str__(self):
        return f"{self.user} | {self.period_start} ~ {self.period_end}"
```

- [ ] **Step 4: Create admin.py**

Create `backend/apps/kpi/admin.py`:

```python
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import KPISnapshot


@admin.register(KPISnapshot)
class KPISnapshotAdmin(ModelAdmin):
    list_display = ("user", "period_start", "period_end", "computed_at")
    list_filter = ("period_start", "period_end")
    search_fields = ("user__username", "user__name")
    readonly_fields = ("id", "computed_at", "created_at")
```

- [ ] **Step 5: Register app in settings.py**

In `backend/config/settings.py`, add `"apps.kpi"` after `"apps.notifications"` in INSTALLED_APPS:

```python
    "apps.notifications",
    "apps.kpi",
```

- [ ] **Step 6: Create and run migration**

```bash
cd backend && uv run python manage.py makemigrations kpi
cd backend && uv run python manage.py migrate
```

- [ ] **Step 7: Write model test**

Create `backend/tests/test_kpi_metrics.py`:

```python
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
```

- [ ] **Step 8: Run test to verify it passes**

```bash
cd backend && uv run pytest tests/test_kpi_metrics.py -v
```

Expected: 2 tests PASS

- [ ] **Step 9: Commit**

```bash
git add backend/apps/kpi/ backend/config/settings.py backend/tests/test_kpi_metrics.py
git commit -m "feat(kpi): add KPISnapshot model and app scaffold"
```

---

## Task 2: Issue Metrics Computation

**Files:**
- Create: `backend/apps/kpi/metrics.py`
- Test: `backend/tests/test_kpi_metrics.py` (append)

- [ ] **Step 1: Write the failing test for issue metrics**

Append to `backend/tests/test_kpi_metrics.py`:

```python
from datetime import date, timedelta
from apps.kpi.metrics import compute_issue_metrics
from tests.factories import IssueFactory, ActivityFactory, ProjectFactory


class TestIssueMetrics:
    def test_basic_issue_metrics(self, site_settings):
        user = UserFactory()
        project = ProjectFactory()
        now = timezone.now()
        start = date(2026, 4, 1)
        end = date(2026, 4, 15)

        # Create 3 resolved issues assigned to user
        for i, prio in enumerate(["P0", "P1", "P2"]):
            issue = IssueFactory(
                project=project, assignee=user, priority=prio,
                status="已解决", created_by=UserFactory(),
                resolved_at=now - timedelta(hours=10 * (i + 1)),
                created_at=now - timedelta(hours=20 * (i + 1)),
            )
            ActivityFactory(user=user, issue=issue, action="resolved")

        # 1 unresolved issue
        IssueFactory(
            project=project, assignee=user, priority="P3",
            status="进行中", created_by=UserFactory(),
        )

        result = compute_issue_metrics(user, start, end)

        assert result["assigned_count"] == 4
        assert result["resolved_count"] == 3
        assert result["resolution_rate"] == pytest.approx(0.75)
        assert result["avg_resolution_hours"] > 0
        assert "priority_breakdown" in result
        assert result["priority_breakdown"]["P0"]["resolved"] == 1

    def test_issue_metrics_empty(self, site_settings):
        user = UserFactory()
        result = compute_issue_metrics(user, date(2026, 4, 1), date(2026, 4, 15))

        assert result["assigned_count"] == 0
        assert result["resolved_count"] == 0
        assert result["resolution_rate"] == 0
        assert result["avg_resolution_hours"] == 0

    def test_helper_count(self, site_settings):
        user = UserFactory()
        project = ProjectFactory()
        issue = IssueFactory(
            project=project, assignee=UserFactory(),
            status="已解决", created_by=UserFactory(),
            resolved_at=timezone.now(),
        )
        issue.helpers.add(user)

        result = compute_issue_metrics(user, date(2026, 1, 1), date(2026, 12, 31))
        assert result["as_helper_count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_kpi_metrics.py::TestIssueMetrics -v
```

Expected: FAIL with `ImportError: cannot import name 'compute_issue_metrics'`

- [ ] **Step 3: Implement compute_issue_metrics**

Create `backend/apps/kpi/metrics.py`:

```python
from datetime import date, timedelta

from django.db.models import Avg, Count, F, Q
from django.utils import timezone

from apps.issues.models import Activity, Issue
from apps.repos.models import Commit, GitAuthorAlias

PRIORITY_WEIGHTS = {"P0": 4, "P1": 3, "P2": 2, "P3": 1}
RESOLVED_STATUSES = ("已解决", "已关闭")


def compute_issue_metrics(user, period_start: date, period_end: date) -> dict:
    """Aggregate issue metrics for a single user within a date range."""
    start_dt = timezone.make_aware(
        timezone.datetime.combine(period_start, timezone.datetime.min.time())
    )
    end_dt = timezone.make_aware(
        timezone.datetime.combine(period_end, timezone.datetime.max.time())
    )

    assigned_qs = Issue.objects.filter(
        assignee=user, created_at__lte=end_dt,
    ).exclude(created_at__gt=end_dt)

    assigned_count = assigned_qs.count()

    resolved_qs = assigned_qs.filter(
        status__in=RESOLVED_STATUSES, resolved_at__isnull=False,
        resolved_at__gte=start_dt, resolved_at__lte=end_dt,
    )
    resolved_count = resolved_qs.count()
    resolution_rate = resolved_count / assigned_count if assigned_count else 0

    # Average resolution hours
    avg_hours_agg = resolved_qs.annotate(
        duration=F("resolved_at") - F("created_at")
    ).aggregate(avg=Avg("duration"))
    avg_td = avg_hours_agg["avg"]
    avg_resolution_hours = round(avg_td.total_seconds() / 3600, 1) if avg_td else 0

    # Daily / weekly averages
    total_days = max((period_end - period_start).days, 1)
    daily_resolved_avg = round(resolved_count / total_days, 2)
    weekly_resolved_avg = round(resolved_count / max(total_days / 7, 1), 2)

    # Priority breakdown
    priority_breakdown = {}
    for prio in PRIORITY_WEIGHTS:
        prio_assigned = assigned_qs.filter(priority=prio).count()
        prio_resolved = resolved_qs.filter(priority=prio)
        prio_count = prio_resolved.count()
        prio_avg = prio_resolved.annotate(
            duration=F("resolved_at") - F("created_at")
        ).aggregate(avg=Avg("duration"))["avg"]
        prio_hours = round(prio_avg.total_seconds() / 3600, 1) if prio_avg else 0
        priority_breakdown[prio] = {
            "assigned": prio_assigned,
            "resolved": prio_count,
            "avg_hours": prio_hours,
        }

    # Weighted issue value
    weighted_value = 0
    for issue in resolved_qs:
        weight = PRIORITY_WEIGHTS.get(issue.priority, 1)
        duration = issue.resolved_at - issue.created_at
        hours = duration.total_seconds() / 3600
        helper_count = issue.helpers.count()
        activity_count = Activity.objects.filter(issue=issue).count()
        raw_complexity = hours * 0.4 + helper_count * 0.3 + activity_count * 0.3
        weighted_value += weight * max(raw_complexity, 0.5)
    weighted_value = round(weighted_value, 1)

    # Helper count (issues where user is a helper, not assignee)
    as_helper_count = Issue.objects.filter(
        helpers=user,
        created_at__lte=end_dt,
    ).exclude(assignee=user).distinct().count()

    return {
        "assigned_count": assigned_count,
        "resolved_count": resolved_count,
        "resolution_rate": round(resolution_rate, 3),
        "avg_resolution_hours": avg_resolution_hours,
        "daily_resolved_avg": daily_resolved_avg,
        "weekly_resolved_avg": weekly_resolved_avg,
        "weighted_issue_value": weighted_value,
        "priority_breakdown": priority_breakdown,
        "as_helper_count": as_helper_count,
    }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && uv run pytest tests/test_kpi_metrics.py::TestIssueMetrics -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/kpi/metrics.py backend/tests/test_kpi_metrics.py
git commit -m "feat(kpi): add issue metrics computation"
```

---

## Task 3: Commit Metrics Computation

**Files:**
- Modify: `backend/apps/kpi/metrics.py`
- Test: `backend/tests/test_kpi_metrics.py` (append)

- [ ] **Step 1: Write the failing test for commit metrics**

Append to `backend/tests/test_kpi_metrics.py`:

```python
import re
from apps.kpi.metrics import compute_commit_metrics
from tests.factories import RepoFactory, CommitFactory, GitAuthorAliasFactory


class TestCommitMetrics:
    def test_basic_commit_metrics(self):
        user = UserFactory()
        repo = RepoFactory(clone_status="cloned")
        alias = GitAuthorAliasFactory(repo=repo, user=user, author_email="dev@test.com")

        now = timezone.now()
        for i in range(5):
            CommitFactory(
                repo=repo, author_email="dev@test.com", author_name="Dev",
                message=f"feat(mod{i}): add feature {i}",
                date=now - timedelta(days=i),
                additions=50 + i * 10, deletions=10 + i * 5,
                files_changed=[f"src/module{i}/app.py", f"src/module{i}/test.ts"],
            )
        # Add a fix commit on same file as feat commit 0 (within 72h) = self-introduced bug
        CommitFactory(
            repo=repo, author_email="dev@test.com", author_name="Dev",
            message="fix(mod0): fix regression",
            date=now - timedelta(hours=12),
            additions=5, deletions=3,
            files_changed=["src/module0/app.py"],
        )

        result = compute_commit_metrics(user, date(2026, 1, 1), date(2026, 12, 31))

        assert result["total_commits"] == 6
        assert result["additions"] > 0
        assert result["deletions"] > 0
        assert result["self_introduced_bug_rate"] > 0  # 1 self-fix out of 5 feat commits
        assert ".py" in result["file_type_breadth"]
        assert ".ts" in result["file_type_breadth"]
        assert len(result["work_rhythm"]["by_hour"]) == 24
        assert len(result["work_rhythm"]["by_weekday"]) == 7
        assert result["commit_type_distribution"]["feat"] == 5
        assert result["commit_type_distribution"]["fix"] == 1
        assert len(result["repo_coverage"]) == 1

    def test_commit_metrics_no_commits(self):
        user = UserFactory()
        result = compute_commit_metrics(user, date(2026, 4, 1), date(2026, 4, 15))

        assert result["total_commits"] == 0
        assert result["additions"] == 0
        assert result["self_introduced_bug_rate"] == 0
        assert result["file_type_breadth"] == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_kpi_metrics.py::TestCommitMetrics -v
```

Expected: FAIL with `ImportError: cannot import name 'compute_commit_metrics'`

- [ ] **Step 3: Implement compute_commit_metrics**

Append to `backend/apps/kpi/metrics.py`:

```python
import math
import os
import re
from collections import Counter, defaultdict

CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|refactor|chore|docs|style|test|perf|ci|build)(\(.+\))?[!]?:\s.+"
)


def compute_commit_metrics(user, period_start: date, period_end: date) -> dict:
    """Aggregate commit metrics for a user across all linked repos."""
    start_dt = timezone.make_aware(
        timezone.datetime.combine(period_start, timezone.datetime.min.time())
    )
    end_dt = timezone.make_aware(
        timezone.datetime.combine(period_end, timezone.datetime.max.time())
    )

    # Find all author emails linked to this user
    aliases = GitAuthorAlias.objects.filter(user=user).values_list(
        "author_email", "repo_id", "repo__name"
    )
    if not aliases:
        return _empty_commit_metrics()

    emails = set()
    repo_ids = set()
    repo_names = {}
    for email, repo_id, repo_name in aliases:
        emails.add(email)
        repo_ids.add(repo_id)
        repo_names[repo_id] = repo_name

    commits = Commit.objects.filter(
        repo_id__in=repo_ids,
        author_email__in=emails,
        date__gte=start_dt,
        date__lte=end_dt,
    ).order_by("date")

    commit_list = list(commits.values(
        "repo_id", "author_email", "date", "message",
        "additions", "deletions", "files_changed",
    ))

    if not commit_list:
        return _empty_commit_metrics()

    total_commits = len(commit_list)
    total_additions = sum(c["additions"] for c in commit_list)
    total_deletions = sum(c["deletions"] for c in commit_list)
    lines_changed = total_additions + total_deletions

    # Commit type distribution
    type_counts = Counter()
    conventional_count = 0
    for c in commit_list:
        m = CONVENTIONAL_RE.match(c["message"])
        if m:
            type_counts[m.group(1)] += 1
            conventional_count += 1
        else:
            type_counts["other"] += 1

    conventional_ratio = round(conventional_count / total_commits, 2) if total_commits else 0

    # Self-introduced bug rate
    self_bug_rate = _compute_self_introduced_bug_rate(commit_list)

    # Churn rate
    churn_rate = _compute_churn_rate(commit_list)

    # Commit size distribution
    sizes = [c["additions"] + c["deletions"] for c in commit_list]
    avg_commit_size = round(sum(sizes) / len(sizes)) if sizes else 0
    size_dist = {"small": 0, "medium": 0, "large": 0}
    for s in sizes:
        if s < 50:
            size_dist["small"] += 1
        elif s <= 200:
            size_dist["medium"] += 1
        else:
            size_dist["large"] += 1

    # File type breadth
    all_extensions = set()
    for c in commit_list:
        for f in (c["files_changed"] or []):
            _, ext = os.path.splitext(f)
            if ext:
                all_extensions.add(ext)

    # Work rhythm
    by_hour = [0] * 24
    by_weekday = [0] * 7
    for c in commit_list:
        dt = c["date"]
        by_hour[dt.hour] += 1
        by_weekday[dt.weekday()] += 1

    # Refactor ratio
    refactor_ratio = round(type_counts.get("refactor", 0) / total_commits, 2) if total_commits else 0

    # Repo coverage
    repo_commit_counts = Counter(c["repo_id"] for c in commit_list)
    repo_coverage = [
        {"repo_id": str(rid), "repo_name": repo_names.get(rid, ""), "commits": cnt}
        for rid, cnt in repo_commit_counts.most_common()
    ]

    return {
        "total_commits": total_commits,
        "additions": total_additions,
        "deletions": total_deletions,
        "lines_changed": lines_changed,
        "self_introduced_bug_rate": self_bug_rate,
        "churn_rate": churn_rate,
        "avg_commit_size": avg_commit_size,
        "commit_size_distribution": size_dist,
        "file_type_breadth": sorted(all_extensions),
        "work_rhythm": {"by_hour": by_hour, "by_weekday": by_weekday},
        "refactor_ratio": refactor_ratio,
        "commit_type_distribution": dict(type_counts),
        "repo_coverage": repo_coverage,
        "conventional_ratio": conventional_ratio,
    }


def _compute_self_introduced_bug_rate(commit_list: list) -> float:
    """
    Ratio of feat/refactor commits followed by a fix on the same file within 72h
    by the same author.
    """
    feat_commits = [
        c for c in commit_list
        if CONVENTIONAL_RE.match(c["message"])
        and CONVENTIONAL_RE.match(c["message"]).group(1) in ("feat", "refactor")
    ]
    if not feat_commits:
        return 0

    fix_commits = [
        c for c in commit_list
        if CONVENTIONAL_RE.match(c["message"])
        and CONVENTIONAL_RE.match(c["message"]).group(1) == "fix"
    ]

    self_fix_count = 0
    for feat in feat_commits:
        feat_files = set(feat["files_changed"] or [])
        feat_date = feat["date"]
        for fix in fix_commits:
            fix_date = fix["date"]
            if fix_date <= feat_date:
                continue
            if (fix_date - feat_date).total_seconds() > 72 * 3600:
                continue
            fix_files = set(fix["files_changed"] or [])
            if feat_files & fix_files:
                self_fix_count += 1
                break  # Count each feat only once

    return round(self_fix_count / len(feat_commits), 2)


def _compute_churn_rate(commit_list: list) -> float:
    """
    Ratio of lines that get re-modified within 30 days.
    Simplified: count commits that touch the same file as a prior commit within 30 days.
    """
    if not commit_list:
        return 0

    total_additions = sum(c["additions"] for c in commit_list)
    if total_additions == 0:
        return 0

    churned = 0
    file_history = {}  # file -> (last_date, additions)
    for c in sorted(commit_list, key=lambda x: x["date"]):
        for f in (c["files_changed"] or []):
            if f in file_history:
                prev_date, prev_add = file_history[f]
                if (c["date"] - prev_date).days <= 30:
                    churned += min(c["additions"] + c["deletions"], prev_add)
            file_history[f] = (c["date"], c["additions"])

    return round(min(churned / total_additions, 1.0), 2)


def _empty_commit_metrics() -> dict:
    return {
        "total_commits": 0,
        "additions": 0,
        "deletions": 0,
        "lines_changed": 0,
        "self_introduced_bug_rate": 0,
        "churn_rate": 0,
        "avg_commit_size": 0,
        "commit_size_distribution": {"small": 0, "medium": 0, "large": 0},
        "file_type_breadth": [],
        "work_rhythm": {"by_hour": [0] * 24, "by_weekday": [0] * 7},
        "refactor_ratio": 0,
        "commit_type_distribution": {},
        "repo_coverage": [],
        "conventional_ratio": 0,
    }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && uv run pytest tests/test_kpi_metrics.py::TestCommitMetrics -v
```

Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/kpi/metrics.py backend/tests/test_kpi_metrics.py
git commit -m "feat(kpi): add commit metrics computation"
```

---

## Task 4: Scoring Engine

**Files:**
- Create: `backend/apps/kpi/scoring.py`
- Create: `backend/tests/test_kpi_scoring.py`

- [ ] **Step 1: Write the failing test for scoring**

Create `backend/tests/test_kpi_scoring.py`:

```python
import pytest
from apps.kpi.scoring import compute_scores, compute_rankings


class TestScoring:
    def test_compute_scores_basic(self):
        issue_metrics = {
            "assigned_count": 10,
            "resolved_count": 8,
            "resolution_rate": 0.8,
            "avg_resolution_hours": 12.0,
            "daily_resolved_avg": 1.5,
            "weekly_resolved_avg": 10.5,
            "weighted_issue_value": 120,
            "priority_breakdown": {
                "P0": {"assigned": 3, "resolved": 3, "avg_hours": 4.0},
                "P1": {"assigned": 3, "resolved": 3, "avg_hours": 8.0},
                "P2": {"assigned": 2, "resolved": 1, "avg_hours": 20.0},
                "P3": {"assigned": 2, "resolved": 1, "avg_hours": 30.0},
            },
            "as_helper_count": 5,
        }
        commit_metrics = {
            "total_commits": 50,
            "additions": 3000,
            "deletions": 800,
            "lines_changed": 3800,
            "self_introduced_bug_rate": 0.05,
            "churn_rate": 0.10,
            "avg_commit_size": 76,
            "commit_size_distribution": {"small": 30, "medium": 15, "large": 5},
            "file_type_breadth": [".py", ".vue", ".ts"],
            "refactor_ratio": 0.12,
            "commit_type_distribution": {"feat": 25, "fix": 10, "refactor": 6},
            "repo_coverage": [{"repo_id": "1", "repo_name": "r1", "commits": 50}],
            "conventional_ratio": 0.82,
            "work_rhythm": {"by_hour": [0]*24, "by_weekday": [0]*7},
        }
        scores = compute_scores(issue_metrics, commit_metrics, prev_scores=None)

        assert "efficiency" in scores
        assert "output" in scores
        assert "quality" in scores
        assert "capability" in scores
        assert "growth" in scores
        assert "overall" in scores
        for key in ("efficiency", "output", "quality", "capability", "growth", "overall"):
            assert 0 <= scores[key] <= 100

    def test_growth_with_previous(self):
        metrics = {
            "assigned_count": 10, "resolved_count": 8, "resolution_rate": 0.8,
            "avg_resolution_hours": 12.0, "daily_resolved_avg": 1.5,
            "weekly_resolved_avg": 10.5, "weighted_issue_value": 120,
            "priority_breakdown": {"P0": {"assigned": 1, "resolved": 1, "avg_hours": 4.0},
                "P1": {"assigned": 0, "resolved": 0, "avg_hours": 0},
                "P2": {"assigned": 0, "resolved": 0, "avg_hours": 0},
                "P3": {"assigned": 0, "resolved": 0, "avg_hours": 0}},
            "as_helper_count": 3,
        }
        commit = {
            "total_commits": 50, "additions": 3000, "deletions": 800,
            "lines_changed": 3800, "self_introduced_bug_rate": 0.05,
            "churn_rate": 0.10, "avg_commit_size": 76,
            "commit_size_distribution": {"small": 30, "medium": 15, "large": 5},
            "file_type_breadth": [".py", ".vue", ".ts"],
            "refactor_ratio": 0.12,
            "commit_type_distribution": {"feat": 25, "fix": 10, "refactor": 6},
            "repo_coverage": [{"repo_id": "1", "repo_name": "r1", "commits": 50}],
            "conventional_ratio": 0.82,
            "work_rhythm": {"by_hour": [0]*24, "by_weekday": [0]*7},
        }
        prev = {"efficiency": 50, "output": 50, "quality": 50, "capability": 50}
        scores = compute_scores(metrics, commit, prev_scores=prev)
        # Growth should reflect improvement
        assert scores["growth"] != 50  # Should differ from default

    def test_compute_rankings(self):
        all_scores = [
            {"user_id": "a", "scores": {"efficiency": 90, "output": 80, "quality": 70, "capability": 60, "growth": 50, "overall": 75}},
            {"user_id": "b", "scores": {"efficiency": 60, "output": 70, "quality": 80, "capability": 90, "growth": 60, "overall": 72}},
            {"user_id": "c", "scores": {"efficiency": 70, "output": 60, "quality": 90, "capability": 50, "growth": 70, "overall": 70}},
        ]
        rankings = compute_rankings(all_scores)

        assert rankings["a"]["overall_rank"] == 1
        assert rankings["b"]["overall_rank"] == 2
        assert rankings["c"]["overall_rank"] == 3
        assert rankings["a"]["total_developers"] == 3
        assert rankings["a"]["efficiency_percentile"] == 100  # Highest
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_kpi_scoring.py -v
```

Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement scoring engine**

Create `backend/apps/kpi/scoring.py`:

```python
"""
Five-dimension scoring engine for KPI analysis.

Dimensions:
  1. Efficiency — speed of issue resolution
  2. Output — total work volume
  3. Quality — code and solution quality
  4. Capability — technical breadth and depth
  5. Growth — period-over-period improvement
"""


def compute_scores(
    issue_metrics: dict, commit_metrics: dict, prev_scores: dict | None
) -> dict:
    """
    Compute absolute 0-100 scores for all five dimensions.
    prev_scores: the previous period's {efficiency, output, quality, capability} or None.
    """
    efficiency = _score_efficiency(issue_metrics)
    output = _score_output(issue_metrics, commit_metrics)
    quality = _score_quality(commit_metrics)
    capability = _score_capability(issue_metrics, commit_metrics)
    growth = _score_growth(
        {"efficiency": efficiency, "output": output, "quality": quality, "capability": capability},
        prev_scores,
    )

    overall = round(
        efficiency * 0.25 + output * 0.25 + quality * 0.25
        + capability * 0.15 + growth * 0.10
    )

    return {
        "efficiency": efficiency,
        "output": output,
        "quality": quality,
        "capability": capability,
        "growth": growth,
        "overall": _clamp(overall),
    }


def compute_rankings(all_user_scores: list[dict]) -> dict:
    """
    Compute team rankings/percentiles from a list of
    [{"user_id": ..., "scores": {...}}, ...].
    Returns {user_id: {"efficiency_percentile": ..., "overall_rank": ..., ...}}.
    """
    n = len(all_user_scores)
    if n == 0:
        return {}

    sorted_by_overall = sorted(
        all_user_scores, key=lambda x: x["scores"]["overall"], reverse=True
    )

    dims = ("efficiency", "output", "quality", "capability", "growth")
    dim_sorted = {}
    for dim in dims:
        dim_sorted[dim] = sorted(
            [s["scores"][dim] for s in all_user_scores]
        )

    rankings = {}
    for rank_idx, entry in enumerate(sorted_by_overall, 1):
        uid = entry["user_id"]
        r = {"overall_rank": rank_idx, "total_developers": n}
        for dim in dims:
            val = entry["scores"][dim]
            below = sum(1 for v in dim_sorted[dim] if v < val)
            pct = round(below / max(n - 1, 1) * 100) if n > 1 else 50
            r[f"{dim}_percentile"] = pct
        rankings[uid] = r

    return rankings


# ─── Dimension scorers ────────────────────────────────────────


def _score_efficiency(im: dict) -> int:
    """
    40% daily resolved avg + 40% speed (inverse of avg hours) + 20% P0/P1 speed.
    All mapped to 0-100 using saturation curves.
    """
    daily = _saturate(im.get("daily_resolved_avg", 0), ceiling=5.0)
    avg_hours = im.get("avg_resolution_hours", 0)
    speed = _saturate(1 / max(avg_hours, 0.5), ceiling=1.0) if avg_hours else 0
    p0p1_hours = _p0p1_avg_hours(im)
    p0p1_speed = _saturate(1 / max(p0p1_hours, 0.5), ceiling=0.5) if p0p1_hours else 0

    return _clamp(round(daily * 0.4 + speed * 0.4 + p0p1_speed * 0.2))


def _score_output(im: dict, cm: dict) -> int:
    """
    40% weighted issue value + 30% resolved count + 20% commit volume + 10% repo breadth.
    """
    value = _saturate(im.get("weighted_issue_value", 0), ceiling=500)
    resolved = _saturate(im.get("resolved_count", 0), ceiling=30)
    commit_vol = _saturate(
        cm.get("total_commits", 0) + cm.get("lines_changed", 0) / 100, ceiling=200
    )
    repos = _saturate(len(cm.get("repo_coverage", [])), ceiling=5)

    return _clamp(round(value * 0.4 + resolved * 0.3 + commit_vol * 0.2 + repos * 0.1))


def _score_quality(cm: dict) -> int:
    """
    30% inv(self_bug_rate) + 25% inv(churn_rate) + 20% commit_size_score + 25% conventional_ratio.
    """
    bug = 100 - _saturate(cm.get("self_introduced_bug_rate", 0) * 100, ceiling=30) * 100 / 100
    churn = 100 - _saturate(cm.get("churn_rate", 0) * 100, ceiling=40) * 100 / 100
    size_score = _commit_size_score(cm.get("avg_commit_size", 0))
    conventional = cm.get("conventional_ratio", 0) * 100

    return _clamp(round(bug * 0.30 + churn * 0.25 + size_score * 0.20 + conventional * 0.25))


def _score_capability(im: dict, cm: dict) -> int:
    """
    25% file type breadth + 25% repo coverage + 25% P0 handling ratio + 25% helper participation.
    """
    types = _saturate(len(cm.get("file_type_breadth", [])), ceiling=8)
    repos = _saturate(len(cm.get("repo_coverage", [])), ceiling=5)
    p0_ratio = _p0_handling_ratio(im)
    helper = _saturate(im.get("as_helper_count", 0), ceiling=10)

    return _clamp(round(types * 0.25 + repos * 0.25 + p0_ratio * 0.25 + helper * 0.25))


def _score_growth(current: dict, prev: dict | None) -> int:
    """
    Average improvement across 4 dimensions vs previous period.
    No history → 50 (neutral).
    """
    if not prev:
        return 50

    dims = ("efficiency", "output", "quality", "capability")
    changes = []
    for dim in dims:
        old = prev.get(dim, 50)
        new = current.get(dim, 50)
        if old == 0:
            change = 100 if new > 0 else 0
        else:
            change = (new - old) / old * 100
        changes.append(change)

    avg_change = sum(changes) / len(changes) if changes else 0
    # Map: -50% → 0, 0% → 50, +50% → 100
    return _clamp(round(50 + avg_change))


# ─── Helpers ──────────────────────────────────────────────────


def _saturate(value: float, ceiling: float) -> float:
    """Map value to 0-100 with a ceiling (values >= ceiling → 100)."""
    if ceiling <= 0:
        return 0
    return min(value / ceiling, 1.0) * 100


def _clamp(score: int | float) -> int:
    return max(0, min(100, int(score)))


def _p0p1_avg_hours(im: dict) -> float:
    pb = im.get("priority_breakdown", {})
    total_hours = 0
    count = 0
    for prio in ("P0", "P1"):
        data = pb.get(prio, {})
        resolved = data.get("resolved", 0)
        avg_h = data.get("avg_hours", 0)
        if resolved > 0:
            total_hours += avg_h * resolved
            count += resolved
    return total_hours / count if count else 0


def _p0_handling_ratio(im: dict) -> float:
    """Percentage of P0 issues in user's resolved workload (0-100)."""
    pb = im.get("priority_breakdown", {})
    total_resolved = im.get("resolved_count", 0)
    p0_resolved = pb.get("P0", {}).get("resolved", 0)
    if total_resolved == 0:
        return 0
    return min(p0_resolved / total_resolved * 100, 100)


def _commit_size_score(avg_size: int) -> float:
    """
    Ideal avg commit size is 50-150 lines.
    Score decreases as it deviates from this range.
    """
    if avg_size == 0:
        return 0
    ideal_center = 100
    deviation = abs(avg_size - ideal_center)
    return max(0, 100 - deviation * 0.5)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && uv run pytest tests/test_kpi_scoring.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/kpi/scoring.py backend/tests/test_kpi_scoring.py
git commit -m "feat(kpi): add 5-dimension scoring engine"
```

---

## Task 5: Suggestions Engine

**Files:**
- Create: `backend/apps/kpi/suggestions.py`
- Create: `backend/tests/test_kpi_suggestions.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_kpi_suggestions.py`:

```python
import pytest
from apps.kpi.suggestions import generate_suggestions


class TestSuggestions:
    def test_shortcomings_detected(self):
        scores = {"efficiency": 40, "output": 70, "quality": 30, "capability": 60, "growth": 50, "overall": 50}
        issue_metrics = {
            "assigned_count": 10, "resolved_count": 3, "resolution_rate": 0.3,
            "avg_resolution_hours": 48.0, "daily_resolved_avg": 0.5,
            "priority_breakdown": {
                "P0": {"assigned": 1, "resolved": 0, "avg_hours": 0},
                "P1": {"assigned": 2, "resolved": 1, "avg_hours": 24},
                "P2": {"assigned": 4, "resolved": 1, "avg_hours": 48},
                "P3": {"assigned": 3, "resolved": 1, "avg_hours": 72},
            },
            "as_helper_count": 0, "weighted_issue_value": 20,
            "weekly_resolved_avg": 3.5,
        }
        commit_metrics = {
            "total_commits": 20, "self_introduced_bug_rate": 0.25,
            "churn_rate": 0.30, "avg_commit_size": 400,
            "conventional_ratio": 0.3, "file_type_breadth": [".py"],
            "refactor_ratio": 0.0,
            "commit_type_distribution": {"feat": 10, "fix": 8, "other": 2},
            "repo_coverage": [], "additions": 1000, "deletions": 500,
            "lines_changed": 1500,
            "commit_size_distribution": {"small": 2, "medium": 5, "large": 13},
            "work_rhythm": {"by_hour": [0]*24, "by_weekday": [0]*7},
        }
        team_avgs = {"efficiency": 60, "output": 65, "quality": 60, "capability": 55}

        result = generate_suggestions(scores, issue_metrics, commit_metrics, team_avgs, prev_scores=None)

        assert len(result["shortcomings"]) > 0
        assert result["profile"]  # Should generate a capability profile
        dims = [s["dimension"] for s in result["shortcomings"]]
        assert "quality" in dims  # Bug rate 25% should trigger

    def test_trend_suggestions(self):
        scores = {"efficiency": 80, "output": 70, "quality": 85, "capability": 75, "growth": 65, "overall": 77}
        issue_metrics = {
            "assigned_count": 10, "resolved_count": 8, "resolution_rate": 0.8,
            "avg_resolution_hours": 12.0, "daily_resolved_avg": 1.5,
            "priority_breakdown": {"P0": {"assigned": 2, "resolved": 2, "avg_hours": 4},
                "P1": {"assigned": 0, "resolved": 0, "avg_hours": 0},
                "P2": {"assigned": 0, "resolved": 0, "avg_hours": 0},
                "P3": {"assigned": 0, "resolved": 0, "avg_hours": 0}},
            "as_helper_count": 3, "weighted_issue_value": 100,
            "weekly_resolved_avg": 10.5,
        }
        commit_metrics = {
            "total_commits": 50, "self_introduced_bug_rate": 0.02,
            "churn_rate": 0.08, "avg_commit_size": 80,
            "conventional_ratio": 0.9, "file_type_breadth": [".py", ".vue"],
            "refactor_ratio": 0.1,
            "commit_type_distribution": {"feat": 30, "fix": 5, "refactor": 5},
            "repo_coverage": [{"repo_id": "1", "repo_name": "r1", "commits": 50}],
            "additions": 3000, "deletions": 800, "lines_changed": 3800,
            "commit_size_distribution": {"small": 30, "medium": 15, "large": 5},
            "work_rhythm": {"by_hour": [0]*24, "by_weekday": [0]*7},
        }
        team_avgs = {"efficiency": 60, "output": 65, "quality": 60, "capability": 55}
        prev = {"efficiency": 60, "output": 65, "quality": 80, "capability": 70}

        result = generate_suggestions(scores, issue_metrics, commit_metrics, team_avgs, prev_scores=prev)
        assert "trends" in result
        # Efficiency went from 60 to 80 = +33% → should trigger positive trend
        assert any(t["direction"] == "up" for t in result["trends"])

    def test_balanced_profile(self):
        scores = {"efficiency": 72, "output": 74, "quality": 73, "capability": 71, "growth": 70, "overall": 72}
        issue_metrics = {
            "assigned_count": 10, "resolved_count": 8, "resolution_rate": 0.8,
            "avg_resolution_hours": 12.0, "daily_resolved_avg": 1.5,
            "priority_breakdown": {"P0": {"assigned": 2, "resolved": 2, "avg_hours": 4},
                "P1": {"assigned": 0, "resolved": 0, "avg_hours": 0},
                "P2": {"assigned": 0, "resolved": 0, "avg_hours": 0},
                "P3": {"assigned": 0, "resolved": 0, "avg_hours": 0}},
            "as_helper_count": 3, "weighted_issue_value": 100,
            "weekly_resolved_avg": 10.5,
        }
        commit_metrics = {
            "total_commits": 50, "self_introduced_bug_rate": 0.05,
            "churn_rate": 0.1, "avg_commit_size": 80,
            "conventional_ratio": 0.85, "file_type_breadth": [".py", ".vue"],
            "refactor_ratio": 0.1,
            "commit_type_distribution": {"feat": 30, "fix": 5, "refactor": 5},
            "repo_coverage": [{"repo_id": "1", "repo_name": "r1", "commits": 50}],
            "additions": 3000, "deletions": 800, "lines_changed": 3800,
            "commit_size_distribution": {"small": 30, "medium": 15, "large": 5},
            "work_rhythm": {"by_hour": [0]*24, "by_weekday": [0]*7},
        }
        team_avgs = {"efficiency": 60, "output": 65, "quality": 60, "capability": 55}

        result = generate_suggestions(scores, issue_metrics, commit_metrics, team_avgs, prev_scores=None)
        assert "均衡" in result["profile"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_kpi_suggestions.py -v
```

Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement suggestions engine**

Create `backend/apps/kpi/suggestions.py`:

```python
"""
Rule-based suggestion engine for KPI improvement recommendations.
"""

DIM_LABELS = {
    "efficiency": "效率",
    "output": "产出",
    "quality": "质量",
    "capability": "能力",
    "growth": "成长",
}

PROFILES = {
    ("efficiency", "quality"): "快速响应型，质量有提升空间",
    ("efficiency", "capability"): "快速响应型，建议拓展技术广度",
    ("efficiency", "output"): "快速响应型，可提升产出总量",
    ("output", "efficiency"): "高产出型，可适当提升响应速度",
    ("output", "quality"): "高产出型，质量有提升空间",
    ("output", "capability"): "高产出型，建议拓展技术广度",
    ("quality", "efficiency"): "精工细作型，可适当提升响应速度",
    ("quality", "output"): "精工细作型，可提升产出总量",
    ("quality", "capability"): "精工细作型，建议拓展技术广度",
    ("capability", "efficiency"): "技术全面型，可适当提升响应速度",
    ("capability", "output"): "技术全面型，可聚焦提升产出量",
    ("capability", "quality"): "技术全面型，质量有提升空间",
}


def generate_suggestions(
    scores: dict,
    issue_metrics: dict,
    commit_metrics: dict,
    team_avgs: dict,
    prev_scores: dict | None,
) -> dict:
    """Generate improvement suggestions based on scores, metrics, and trends."""
    shortcomings = _detect_shortcomings(scores, issue_metrics, commit_metrics, team_avgs)
    trends = _detect_trends(scores, prev_scores)
    profile = _generate_profile(scores)

    return {
        "shortcomings": shortcomings,
        "trends": trends,
        "profile": profile,
    }


def _detect_shortcomings(
    scores: dict, im: dict, cm: dict, team_avgs: dict
) -> list[dict]:
    """Rule-based shortcoming detection."""
    items = []

    # Efficiency below team avg
    if scores.get("efficiency", 0) < team_avgs.get("efficiency", 50):
        avg_h = im.get("avg_resolution_hours", 0)
        items.append({
            "dimension": "efficiency",
            "message": f"平均解决耗时 {avg_h}h，建议关注问题分解和时间管理",
            "severity": "medium",
        })

    # Self-introduced bug rate
    bug_rate = cm.get("self_introduced_bug_rate", 0)
    if bug_rate > 0.1:
        items.append({
            "dimension": "quality",
            "message": f"自引入 Bug 率 {round(bug_rate * 100)}%，建议加强代码自测",
            "severity": "high",
        })

    # Churn rate
    churn = cm.get("churn_rate", 0)
    if churn > 0.2:
        items.append({
            "dimension": "quality",
            "message": f"代码流失率 {round(churn * 100)}%，部分代码稳定性不足，建议加强设计评审",
            "severity": "medium",
        })

    # Large commits
    avg_size = cm.get("avg_commit_size", 0)
    if avg_size > 300:
        items.append({
            "dimension": "quality",
            "message": f"平均每次提交 {avg_size} 行，建议拆分为更小的原子提交",
            "severity": "low",
        })

    # Low P0 handling
    pb = im.get("priority_breakdown", {})
    resolved = im.get("resolved_count", 0)
    p0_resolved = pb.get("P0", {}).get("resolved", 0)
    if resolved > 0 and p0_resolved / resolved < 0.1 and pb.get("P0", {}).get("assigned", 0) > 0:
        pct = round(p0_resolved / resolved * 100)
        items.append({
            "dimension": "capability",
            "message": f"高优先级问题处理占比仅 {pct}%，建议提升紧急响应能力",
            "severity": "medium",
        })

    # Low conventional ratio
    conv = cm.get("conventional_ratio", 0)
    if conv < 0.5 and cm.get("total_commits", 0) > 0:
        items.append({
            "dimension": "quality",
            "message": f"仅 {round(conv * 100)}% 的提交遵循规范格式，建议统一提交信息规范",
            "severity": "low",
        })

    # Sort by severity
    severity_order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda x: severity_order.get(x["severity"], 3))
    return items


def _detect_trends(scores: dict, prev_scores: dict | None) -> list[dict]:
    """Detect period-over-period changes."""
    if not prev_scores:
        return []

    trends = []
    dims = ("efficiency", "output", "quality", "capability")
    for dim in dims:
        old = prev_scores.get(dim, 0)
        new = scores.get(dim, 0)
        if old == 0:
            continue
        change = round((new - old) / old * 100)
        if abs(change) < 5:
            continue

        label = DIM_LABELS.get(dim, dim)
        if change > 10:
            trends.append({
                "dimension": dim,
                "direction": "up",
                "change_percent": change,
                "message": f"{label}评分本期提升 {change}%，保持势头",
            })
        elif change < -10:
            trends.append({
                "dimension": dim,
                "direction": "down",
                "change_percent": change,
                "message": f"{label}评分本期下降 {abs(change)}%，关注是否有阻塞因素",
            })
        elif change > 0:
            trends.append({
                "dimension": dim,
                "direction": "up",
                "change_percent": change,
                "message": f"{label}评分小幅提升 {change}%",
            })
        else:
            trends.append({
                "dimension": dim,
                "direction": "down",
                "change_percent": change,
                "message": f"{label}评分小幅下降 {abs(change)}%",
            })

    return trends


def _generate_profile(scores: dict) -> str:
    """Generate a one-line capability profile based on highest/lowest dimension."""
    dims = {k: scores.get(k, 0) for k in ("efficiency", "output", "quality", "capability")}
    if not dims:
        return "数据不足，暂无画像"

    values = list(dims.values())
    if max(values) - min(values) < 10:
        return "均衡发展型，各维度表现稳定"

    highest = max(dims, key=dims.get)
    lowest = min(dims, key=dims.get)

    return PROFILES.get((highest, lowest), f"{DIM_LABELS[highest]}突出，{DIM_LABELS[lowest]}有提升空间")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && uv run pytest tests/test_kpi_suggestions.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/kpi/suggestions.py backend/tests/test_kpi_suggestions.py
git commit -m "feat(kpi): add suggestion rule engine with capability profiles"
```

---

## Task 6: KPI Orchestrator Service

**Files:**
- Create: `backend/apps/kpi/services.py`
- Modify: `backend/tests/test_kpi_metrics.py` (append integration test)

- [ ] **Step 1: Write the failing integration test**

Append to `backend/tests/test_kpi_metrics.py`:

```python
from apps.kpi.services import KPIService
from django.contrib.auth.models import Group


class TestKPIService:
    def test_refresh_computes_snapshots(self, site_settings):
        group, _ = Group.objects.get_or_create(name="开发者")
        user1 = UserFactory()
        user1.groups.add(group)
        user2 = UserFactory()
        user2.groups.add(group)
        project = ProjectFactory()

        # Create some issues
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
        from apps.kpi.models import KPISnapshot
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

        # Refresh again — should update, not duplicate
        KPIService().refresh(start, end, role="开发者")
        assert KPISnapshot.objects.count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_kpi_metrics.py::TestKPIService -v
```

Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement KPI orchestrator service**

Create `backend/apps/kpi/services.py`:

```python
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from .metrics import compute_commit_metrics, compute_issue_metrics
from .models import KPISnapshot
from .scoring import compute_rankings, compute_scores
from .suggestions import generate_suggestions

User = get_user_model()


class KPIService:
    def refresh(
        self, period_start: date, period_end: date, role: str | None = None
    ) -> dict:
        """
        Compute KPI snapshots for all target users.
        Returns {"user_count": N, "computed_at": datetime}.
        """
        users = self._get_target_users(role)
        now = timezone.now()

        # Phase 1: Compute raw metrics + absolute scores for each user
        user_data = []
        for user in users:
            issue_m = compute_issue_metrics(user, period_start, period_end)
            commit_m = compute_commit_metrics(user, period_start, period_end)
            prev_scores = self._get_previous_scores(user, period_start)
            scores = compute_scores(issue_m, commit_m, prev_scores)
            user_data.append({
                "user": user,
                "issue_metrics": issue_m,
                "commit_metrics": commit_m,
                "scores": scores,
                "prev_scores": prev_scores,
            })

        # Phase 2: Compute team rankings
        all_scores = [
            {"user_id": str(d["user"].pk), "scores": d["scores"]}
            for d in user_data
        ]
        rankings_map = compute_rankings(all_scores)

        # Phase 3: Compute team averages for suggestions
        team_avgs = self._compute_team_averages(user_data)

        # Phase 4: Generate suggestions + store snapshots
        for d in user_data:
            uid = str(d["user"].pk)
            rankings = rankings_map.get(uid, {})
            suggestions = generate_suggestions(
                d["scores"], d["issue_metrics"], d["commit_metrics"],
                team_avgs, d["prev_scores"],
            )

            KPISnapshot.objects.update_or_create(
                user=d["user"],
                period_start=period_start,
                period_end=period_end,
                defaults={
                    "issue_metrics": d["issue_metrics"],
                    "commit_metrics": d["commit_metrics"],
                    "scores": d["scores"],
                    "rankings": rankings,
                    "suggestions": suggestions,
                    "computed_at": now,
                },
            )

        return {"user_count": len(users), "computed_at": now.isoformat()}

    def _get_target_users(self, role: str | None):
        qs = User.objects.filter(is_active=True, is_bot=False)
        if role:
            qs = qs.filter(groups__name=role)
        return list(qs.distinct())

    def _get_previous_scores(self, user, current_start: date) -> dict | None:
        prev = (
            KPISnapshot.objects.filter(user=user, period_end__lt=current_start)
            .order_by("-period_end")
            .first()
        )
        return prev.scores if prev else None

    def _compute_team_averages(self, user_data: list) -> dict:
        if not user_data:
            return {}
        dims = ("efficiency", "output", "quality", "capability")
        avgs = {}
        for dim in dims:
            vals = [d["scores"].get(dim, 0) for d in user_data]
            avgs[dim] = round(sum(vals) / len(vals)) if vals else 0
        return avgs
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && uv run pytest tests/test_kpi_metrics.py::TestKPIService -v
```

Expected: 2 tests PASS

- [ ] **Step 5: Run all KPI tests to verify nothing broke**

```bash
cd backend && uv run pytest tests/test_kpi_metrics.py tests/test_kpi_scoring.py tests/test_kpi_suggestions.py -v
```

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/kpi/services.py backend/tests/test_kpi_metrics.py
git commit -m "feat(kpi): add KPI orchestrator service"
```

---

## Task 7: API — Serializers + Team Dashboard View

**Files:**
- Create: `backend/apps/kpi/serializers.py`
- Create: `backend/apps/kpi/views.py`
- Create: `backend/apps/kpi/urls.py`
- Modify: `backend/apps/urls.py`
- Create: `backend/tests/test_kpi_api.py`

- [ ] **Step 1: Write the failing API test for team endpoint**

Create `backend/tests/test_kpi_api.py`:

```python
import pytest
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from tests.factories import UserFactory, IssueFactory, ProjectFactory
from apps.kpi.models import KPISnapshot

pytestmark = pytest.mark.django_db


@pytest.fixture
def kpi_manager_client(api_client):
    """Client with view_kpisnapshot + refresh_kpi permissions."""
    user = UserFactory()
    group, _ = Group.objects.get_or_create(name="管理员")
    ct = ContentType.objects.get_for_model(KPISnapshot)
    perms = Permission.objects.filter(content_type=ct)
    group.permissions.add(*perms)
    # Also add issue/user view perms for full access
    group.permissions.add(*Permission.objects.filter(
        content_type__app_label__in=["issues", "users", "repos"]
    ))
    user.groups.add(group)
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def kpi_dev_client(api_client):
    """Client with only view_own_kpi permission."""
    user = UserFactory()
    group, _ = Group.objects.get_or_create(name="开发者")
    ct = ContentType.objects.get_for_model(KPISnapshot)
    perm = Permission.objects.get(content_type=ct, codename="view_own_kpi")
    group.permissions.add(perm)
    user.groups.add(group)
    api_client.force_authenticate(user=user)
    api_client._user = user  # Store for later reference
    return api_client


def _create_snapshot(user, **kwargs):
    defaults = {
        "period_start": date(2026, 4, 1),
        "period_end": date(2026, 4, 15),
        "issue_metrics": {"assigned_count": 10, "resolved_count": 8},
        "commit_metrics": {"total_commits": 50},
        "scores": {"efficiency": 80, "output": 75, "quality": 90, "capability": 70, "growth": 60, "overall": 77},
        "rankings": {"overall_rank": 1, "total_developers": 2},
        "suggestions": {"profile": "均衡发展型", "shortcomings": [], "trends": []},
        "computed_at": timezone.now(),
    }
    defaults.update(kwargs)
    return KPISnapshot.objects.create(user=user, **defaults)


class TestTeamDashboardAPI:
    def test_team_endpoint_returns_data(self, kpi_manager_client):
        user1 = UserFactory()
        user2 = UserFactory()
        _create_snapshot(user1, scores={"efficiency": 90, "output": 85, "quality": 80, "capability": 75, "growth": 70, "overall": 82})
        _create_snapshot(user2, scores={"efficiency": 60, "output": 65, "quality": 70, "capability": 55, "growth": 50, "overall": 62})

        resp = kpi_manager_client.get("/api/kpi/team/?start=2026-04-01&end=2026-04-15")
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "developers" in data
        assert len(data["developers"]) == 2
        # Should be sorted by overall desc
        assert data["developers"][0]["scores"]["overall"] >= data["developers"][1]["scores"]["overall"]

    def test_team_endpoint_forbidden_for_dev(self, kpi_dev_client):
        resp = kpi_dev_client.get("/api/kpi/team/?start=2026-04-01&end=2026-04-15")
        assert resp.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_kpi_api.py::TestTeamDashboardAPI -v
```

Expected: FAIL (URLs not configured yet)

- [ ] **Step 3: Create serializers**

Create `backend/apps/kpi/serializers.py`:

```python
from rest_framework import serializers
from .models import KPISnapshot


class KPITeamDeveloperSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id")
    user_name = serializers.CharField(source="user.name")
    avatar = serializers.CharField(source="user.avatar", default="")

    class Meta:
        model = KPISnapshot
        fields = [
            "user_id", "user_name", "avatar",
            "scores", "rankings",
        ]
        read_only_fields = fields


class KPISummarySerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id")
    user_name = serializers.CharField(source="user.name")
    avatar = serializers.CharField(source="user.avatar", default="")
    groups = serializers.SerializerMethodField()

    class Meta:
        model = KPISnapshot
        fields = [
            "user_id", "user_name", "avatar", "groups",
            "scores", "rankings", "period_start", "period_end", "computed_at",
        ]
        read_only_fields = fields

    def get_groups(self, obj):
        return list(obj.user.groups.values_list("name", flat=True))


class KPIIssueMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = KPISnapshot
        fields = ["issue_metrics"]
        read_only_fields = fields


class KPICommitMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = KPISnapshot
        fields = ["commit_metrics"]
        read_only_fields = fields


class KPISuggestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = KPISnapshot
        fields = ["suggestions"]
        read_only_fields = fields
```

- [ ] **Step 4: Create views**

Create `backend/apps/kpi/views.py`:

```python
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Avg
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.permissions import FullDjangoModelPermissions

from .models import KPISnapshot
from .serializers import (
    KPICommitMetricsSerializer,
    KPIIssueMetricsSerializer,
    KPISuggestionsSerializer,
    KPISummarySerializer,
    KPITeamDeveloperSerializer,
)
from .services import KPIService

User = get_user_model()


def _parse_period(request):
    """Parse period from query params. Returns (start_date, end_date)."""
    start = request.query_params.get("start")
    end = request.query_params.get("end")
    period = request.query_params.get("period")

    today = date.today()
    if start and end:
        return date.fromisoformat(start), date.fromisoformat(end)
    elif period == "week":
        start = today - timedelta(days=today.weekday())
        return start, today
    elif period == "quarter":
        q_start_month = ((today.month - 1) // 3) * 3 + 1
        return date(today.year, q_start_month, 1), today
    else:  # default: month
        return today.replace(day=1), today


class KPITeamView(APIView):
    """GET /api/kpi/team/ — Team KPI dashboard (managers only)."""
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = KPISnapshot.objects.none()  # For permission check

    def get(self, request):
        start, end = _parse_period(request)
        role = request.query_params.get("role")

        snapshots = (
            KPISnapshot.objects.filter(period_start=start, period_end=end)
            .select_related("user")
            .order_by("-scores__overall")
        )
        if role:
            snapshots = snapshots.filter(user__groups__name=role)

        devs = KPITeamDeveloperSerializer(snapshots, many=True).data

        # Compute summary
        count = snapshots.count()
        if count:
            total_resolved = sum(
                s.issue_metrics.get("resolved_count", 0) for s in snapshots
            )
            avg_hours = sum(
                s.issue_metrics.get("avg_resolution_hours", 0) for s in snapshots
            ) / count
            avg_overall = sum(s.scores.get("overall", 0) for s in snapshots) / count
        else:
            total_resolved = 0
            avg_hours = 0
            avg_overall = 0

        return Response({
            "summary": {
                "active_count": count,
                "resolved_count": total_resolved,
                "avg_resolution_hours": round(avg_hours, 1),
                "avg_overall_score": round(avg_overall),
            },
            "developers": devs,
        })


class KPIUserSummaryView(APIView):
    """GET /api/kpi/users/{user_id}/summary/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if not self._has_access(request, user_id):
            return Response({"detail": "无权限"}, status=403)

        start, end = _parse_period(request)
        snap = KPISnapshot.objects.filter(
            user_id=user_id, period_start=start, period_end=end
        ).select_related("user").first()
        if not snap:
            return Response({"detail": "暂无数据，请先刷新"}, status=404)

        return Response(KPISummarySerializer(snap).data)

    def _has_access(self, request, user_id):
        if str(request.user.pk) == str(user_id):
            return request.user.has_perm("kpi.view_own_kpi")
        return request.user.has_perm("kpi.view_kpisnapshot")


class KPIUserIssuesView(APIView):
    """GET /api/kpi/users/{user_id}/issues/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if not _has_kpi_access(request, user_id):
            return Response({"detail": "无权限"}, status=403)
        start, end = _parse_period(request)
        snap = KPISnapshot.objects.filter(
            user_id=user_id, period_start=start, period_end=end
        ).first()
        if not snap:
            return Response({"detail": "暂无数据"}, status=404)
        return Response(snap.issue_metrics)


class KPIUserCommitsView(APIView):
    """GET /api/kpi/users/{user_id}/commits/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if not _has_kpi_access(request, user_id):
            return Response({"detail": "无权限"}, status=403)
        start, end = _parse_period(request)
        snap = KPISnapshot.objects.filter(
            user_id=user_id, period_start=start, period_end=end
        ).first()
        if not snap:
            return Response({"detail": "暂无数据"}, status=404)
        return Response(snap.commit_metrics)


class KPIUserTrendsView(APIView):
    """GET /api/kpi/users/{user_id}/trends/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if not _has_kpi_access(request, user_id):
            return Response({"detail": "无权限"}, status=403)
        periods = int(request.query_params.get("periods", 6))
        history = (
            KPISnapshot.objects.filter(user_id=user_id)
            .order_by("-period_end")[:periods]
        )
        return Response({
            "history": [
                {
                    "period_start": str(s.period_start),
                    "period_end": str(s.period_end),
                    "scores": s.scores,
                }
                for s in reversed(list(history))
            ]
        })


class KPIUserSuggestionsView(APIView):
    """GET /api/kpi/users/{user_id}/suggestions/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if not _has_kpi_access(request, user_id):
            return Response({"detail": "无权限"}, status=403)
        start, end = _parse_period(request)
        snap = KPISnapshot.objects.filter(
            user_id=user_id, period_start=start, period_end=end
        ).first()
        if not snap:
            return Response({"detail": "暂无数据"}, status=404)
        return Response(snap.suggestions)


class KPIRefreshView(APIView):
    """POST /api/kpi/refresh/ — Trigger KPI recomputation."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.has_perm("kpi.refresh_kpi"):
            return Response({"detail": "无权限"}, status=403)

        start_str = request.data.get("start")
        end_str = request.data.get("end")
        role = request.data.get("role")

        if start_str and end_str:
            start = date.fromisoformat(start_str)
            end = date.fromisoformat(end_str)
        else:
            today = date.today()
            start = today.replace(day=1)
            end = today

        result = KPIService().refresh(start, end, role=role)
        return Response({
            "status": "completed",
            "computed_at": result["computed_at"],
            "user_count": result["user_count"],
        })


class KPIMeSummaryView(APIView):
    """GET /api/kpi/me/summary/ — Shortcut for current user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.has_perm("kpi.view_own_kpi"):
            return Response({"detail": "无权限"}, status=403)
        start, end = _parse_period(request)
        snap = KPISnapshot.objects.filter(
            user=request.user, period_start=start, period_end=end
        ).select_related("user").first()
        if not snap:
            return Response({"detail": "暂无数据，请先刷新"}, status=404)
        return Response(KPISummarySerializer(snap).data)


class KPIMeIssuesView(APIView):
    """GET /api/kpi/me/issues/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start, end = _parse_period(request)
        snap = KPISnapshot.objects.filter(
            user=request.user, period_start=start, period_end=end
        ).first()
        if not snap:
            return Response({"detail": "暂无数据"}, status=404)
        return Response(snap.issue_metrics)


class KPIMeCommitsView(APIView):
    """GET /api/kpi/me/commits/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start, end = _parse_period(request)
        snap = KPISnapshot.objects.filter(
            user=request.user, period_start=start, period_end=end
        ).first()
        if not snap:
            return Response({"detail": "暂无数据"}, status=404)
        return Response(snap.commit_metrics)


class KPIMeTrendsView(APIView):
    """GET /api/kpi/me/trends/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        periods = int(request.query_params.get("periods", 6))
        history = (
            KPISnapshot.objects.filter(user=request.user)
            .order_by("-period_end")[:periods]
        )
        return Response({
            "history": [
                {"period_start": str(s.period_start), "period_end": str(s.period_end), "scores": s.scores}
                for s in reversed(list(history))
            ]
        })


class KPIMeSuggestionsView(APIView):
    """GET /api/kpi/me/suggestions/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start, end = _parse_period(request)
        snap = KPISnapshot.objects.filter(
            user=request.user, period_start=start, period_end=end
        ).first()
        if not snap:
            return Response({"detail": "暂无数据"}, status=404)
        return Response(snap.suggestions)


def _has_kpi_access(request, user_id) -> bool:
    if str(request.user.pk) == str(user_id):
        return request.user.has_perm("kpi.view_own_kpi")
    return request.user.has_perm("kpi.view_kpisnapshot")
```

- [ ] **Step 5: Create URL routing**

Create `backend/apps/kpi/urls.py`:

```python
from django.urls import path

from .views import (
    KPITeamView,
    KPIUserSummaryView,
    KPIUserIssuesView,
    KPIUserCommitsView,
    KPIUserTrendsView,
    KPIUserSuggestionsView,
    KPIRefreshView,
    KPIMeSummaryView,
    KPIMeIssuesView,
    KPIMeCommitsView,
    KPIMeTrendsView,
    KPIMeSuggestionsView,
)

urlpatterns = [
    path("team/", KPITeamView.as_view(), name="kpi-team"),
    path("refresh/", KPIRefreshView.as_view(), name="kpi-refresh"),
    # /me/ shortcuts (must be before users/<uuid>/ to avoid conflict)
    path("me/summary/", KPIMeSummaryView.as_view(), name="kpi-me-summary"),
    path("me/issues/", KPIMeIssuesView.as_view(), name="kpi-me-issues"),
    path("me/commits/", KPIMeCommitsView.as_view(), name="kpi-me-commits"),
    path("me/trends/", KPIMeTrendsView.as_view(), name="kpi-me-trends"),
    path("me/suggestions/", KPIMeSuggestionsView.as_view(), name="kpi-me-suggestions"),
    # Per-user endpoints
    path("users/<uuid:user_id>/summary/", KPIUserSummaryView.as_view(), name="kpi-user-summary"),
    path("users/<uuid:user_id>/issues/", KPIUserIssuesView.as_view(), name="kpi-user-issues"),
    path("users/<uuid:user_id>/commits/", KPIUserCommitsView.as_view(), name="kpi-user-commits"),
    path("users/<uuid:user_id>/trends/", KPIUserTrendsView.as_view(), name="kpi-user-trends"),
    path("users/<uuid:user_id>/suggestions/", KPIUserSuggestionsView.as_view(), name="kpi-user-suggestions"),
]
```

- [ ] **Step 6: Register URLs in main urlconf**

In `backend/apps/urls.py`, add after the `notifications` line:

```python
    path("kpi/", include("apps.kpi.urls")),
```

- [ ] **Step 7: Run API tests**

```bash
cd backend && uv run pytest tests/test_kpi_api.py -v
```

Expected: 2 tests PASS

- [ ] **Step 8: Add more API tests**

Append to `backend/tests/test_kpi_api.py`:

```python
class TestIndividualKPIAPI:
    def test_user_summary(self, kpi_manager_client):
        user = UserFactory()
        snap = _create_snapshot(user)
        resp = kpi_manager_client.get(f"/api/kpi/users/{user.pk}/summary/?start=2026-04-01&end=2026-04-15")
        assert resp.status_code == 200
        assert resp.json()["scores"]["overall"] == 77

    def test_dev_can_view_own(self, kpi_dev_client):
        user = kpi_dev_client._user
        _create_snapshot(user)
        resp = kpi_dev_client.get(f"/api/kpi/users/{user.pk}/summary/?start=2026-04-01&end=2026-04-15")
        assert resp.status_code == 200

    def test_dev_cannot_view_others(self, kpi_dev_client):
        other = UserFactory()
        _create_snapshot(other)
        resp = kpi_dev_client.get(f"/api/kpi/users/{other.pk}/summary/?start=2026-04-01&end=2026-04-15")
        assert resp.status_code == 403

    def test_trends_endpoint(self, kpi_manager_client):
        user = UserFactory()
        _create_snapshot(user, period_start=date(2026, 3, 1), period_end=date(2026, 3, 31))
        _create_snapshot(user, period_start=date(2026, 4, 1), period_end=date(2026, 4, 15))
        resp = kpi_manager_client.get(f"/api/kpi/users/{user.pk}/trends/?periods=6")
        assert resp.status_code == 200
        assert len(resp.json()["history"]) == 2


class TestRefreshAPI:
    def test_refresh_requires_permission(self, kpi_dev_client):
        resp = kpi_dev_client.post("/api/kpi/refresh/", {})
        assert resp.status_code == 403

    def test_refresh_works_for_manager(self, kpi_manager_client, site_settings):
        resp = kpi_manager_client.post("/api/kpi/refresh/", {
            "start": "2026-04-01", "end": "2026-04-15"
        }, format="json")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"


class TestMeAPI:
    def test_me_summary(self, kpi_dev_client):
        user = kpi_dev_client._user
        _create_snapshot(user)
        resp = kpi_dev_client.get("/api/kpi/me/summary/?start=2026-04-01&end=2026-04-15")
        assert resp.status_code == 200
        assert resp.json()["scores"]["overall"] == 77
```

- [ ] **Step 9: Run all API tests**

```bash
cd backend && uv run pytest tests/test_kpi_api.py -v
```

Expected: All tests PASS

- [ ] **Step 10: Commit**

```bash
git add backend/apps/kpi/serializers.py backend/apps/kpi/views.py backend/apps/kpi/urls.py backend/apps/urls.py backend/tests/test_kpi_api.py
git commit -m "feat(kpi): add API endpoints for team dashboard, individual KPI, and refresh"
```

---

## Task 8: Permissions + PAGE_PERMS Configuration

**Files:**
- Modify: `backend/config/settings.py:158-180` (PAGE_PERMS)
- Modify: `backend/tests/factories.py` (add KPISnapshotFactory)

- [ ] **Step 1: Add KPI route to PAGE_PERMS SEED_ROUTES**

In `backend/config/settings.py`, in the `SEED_ROUTES` list, add after the `/app/users` entry:

```python
        {"path": "/app/kpi", "label": "KPI 分析", "icon": "i-heroicons-chart-bar-square", "permission": "kpi.view_kpisnapshot", "sort_order": 6},
```

And bump `/app/notifications/manage` sort_order from 6 to 7:

```python
        {"path": "/app/notifications/manage", "label": "通知管理", "icon": "i-heroicons-bell-alert", "permission": "notifications.view_notification", "sort_order": 7},
```

- [ ] **Step 2: Add KPI permissions to SEED_GROUPS**

In `backend/config/settings.py`, in `SEED_GROUPS`:

- Add `"kpi"` to the `管理员` apps list:
```python
        "管理员": {"apps": ["projects", "issues", "settings", "repos", "ai", "users", "tools", "notifications", "kpi"]},
```

- Add `view_own_kpi` to `开发者` permissions:
```python
        "开发者": {"permissions": ["view_project", "view_issue", "add_issue", "change_issue", "view_activity", "view_dashboard", "view_analysis", "add_analysis", "view_own_kpi"]},
```

- Add `view_own_kpi` to `测试` permissions:
```python
        "测试": {"permissions": ["view_project", "view_issue", "add_issue", "change_issue", "view_activity", "view_dashboard", "view_analysis", "add_analysis", "view_own_kpi"]},
```

- [ ] **Step 3: Add KPISnapshotFactory**

Append to `backend/tests/factories.py`:

```python
from apps.kpi.models import KPISnapshot


class KPISnapshotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = KPISnapshot

    user = factory.SubFactory(UserFactory)
    period_start = factory.LazyFunction(lambda: tz.now().date().replace(day=1))
    period_end = factory.LazyFunction(lambda: tz.now().date())
    issue_metrics = factory.LazyFunction(lambda: {"assigned_count": 10, "resolved_count": 8})
    commit_metrics = factory.LazyFunction(lambda: {"total_commits": 50})
    scores = factory.LazyFunction(lambda: {
        "efficiency": 70, "output": 75, "quality": 80, "capability": 65, "growth": 50, "overall": 72
    })
    rankings = factory.LazyFunction(lambda: {"overall_rank": 1, "total_developers": 1})
    suggestions = factory.LazyFunction(lambda: {"profile": "均衡发展型", "shortcomings": [], "trends": []})
    computed_at = factory.LazyFunction(tz.now)
```

- [ ] **Step 4: Sync permissions**

```bash
cd backend && uv run python manage.py sync_page_perms
```

- [ ] **Step 5: Run all KPI tests**

```bash
cd backend && uv run pytest tests/test_kpi_metrics.py tests/test_kpi_scoring.py tests/test_kpi_suggestions.py tests/test_kpi_api.py -v
```

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/config/settings.py backend/tests/factories.py
git commit -m "feat(kpi): configure PAGE_PERMS, SEED_GROUPS, and add KPISnapshotFactory"
```

---

## Task 9: Frontend — Team Dashboard Page

**Files:**
- Create: `frontend/app/pages/app/kpi/index.vue`
- Modify: `frontend/app/composables/useNavigation.ts:23-27` (GROUP_DEFS)

- [ ] **Step 1: Add `/app/kpi` to navigation GROUP_DEFS**

In `frontend/app/composables/useNavigation.ts`, update the `用户管理` entry in GROUP_DEFS:

```typescript
  { label: '用户管理', icon: 'i-heroicons-users', paths: ['/app/users', '/app/kpi', '/app/permissions'] },
```

- [ ] **Step 2: Create team dashboard page**

Create `frontend/app/pages/app/kpi/index.vue`:

```vue
<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between flex-wrap gap-4">
      <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">KPI 分析</h1>
      <div class="flex items-center gap-2 flex-wrap">
        <!-- Period shortcuts -->
        <UButtonGroup>
          <UButton
            v-for="p in periodOptions" :key="p.value"
            :label="p.label"
            :variant="activePeriod === p.value ? 'solid' : 'outline'"
            size="sm"
            @click="setPeriod(p.value)"
          />
        </UButtonGroup>

        <!-- Custom date range -->
        <UPopover>
          <UButton icon="i-heroicons-calendar" size="sm" variant="outline" label="自定义" />
          <template #panel>
            <div class="p-3 space-y-2">
              <label class="text-xs text-gray-500">起始日期</label>
              <input type="date" v-model="customStart" class="block w-full rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm" />
              <label class="text-xs text-gray-500">截止日期</label>
              <input type="date" v-model="customEnd" class="block w-full rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm" />
              <UButton label="应用" size="xs" block @click="applyCustom" />
            </div>
          </template>
        </UPopover>

        <!-- Role filter -->
        <USelect v-model="selectedRole" :options="roleOptions" size="sm" class="w-32" />

        <!-- Refresh button -->
        <UButton
          icon="i-heroicons-arrow-path"
          label="刷新数据"
          color="primary"
          size="sm"
          :loading="refreshing"
          @click="refreshData"
        />
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-sm text-gray-400">加载中...</div>
    </div>

    <template v-else-if="data">
      <!-- Summary cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4 text-center">
          <div class="text-xs text-gray-500 dark:text-gray-400">活跃开发者</div>
          <div class="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{{ data.summary.active_count }}</div>
        </div>
        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4 text-center">
          <div class="text-xs text-gray-500 dark:text-gray-400">本周期解决问题</div>
          <div class="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">{{ data.summary.resolved_count }}</div>
        </div>
        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4 text-center">
          <div class="text-xs text-gray-500 dark:text-gray-400">团队平均耗时</div>
          <div class="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">{{ data.summary.avg_resolution_hours }}h</div>
        </div>
        <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4 text-center">
          <div class="text-xs text-gray-500 dark:text-gray-400">团队平均综合分</div>
          <div class="text-2xl font-bold text-purple-600 dark:text-purple-400 mt-1">{{ data.summary.avg_overall_score }}</div>
        </div>
      </div>

      <!-- Developer ranking table -->
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden">
        <UTable :rows="tableRows" :columns="columns" @select="goToProfile">
          <template #rank-data="{ row }">
            <span v-if="row.rank === 1" class="text-lg">🥇</span>
            <span v-else-if="row.rank === 2" class="text-lg">🥈</span>
            <span v-else-if="row.rank === 3" class="text-lg">🥉</span>
            <span v-else class="text-gray-400">{{ row.rank }}</span>
          </template>
          <template #user-data="{ row }">
            <div class="flex items-center gap-2">
              <div class="w-7 h-7 rounded-full bg-crystal-100 dark:bg-crystal-900 flex items-center justify-center text-xs font-bold text-crystal-600">
                {{ row.user_name?.charAt(0)?.toUpperCase() }}
              </div>
              <span>{{ row.user_name }}</span>
            </div>
          </template>
          <template #overall-data="{ row }">
            <span class="font-bold" :class="scoreColor(row.overall)">{{ row.overall }}</span>
          </template>
          <template #trend-data="{ row }">
            <span v-if="row.trend > 0" class="text-emerald-500">↑ {{ row.trend }}%</span>
            <span v-else-if="row.trend < 0" class="text-red-500">↓ {{ Math.abs(row.trend) }}%</span>
            <span v-else class="text-gray-400">— 0%</span>
          </template>
          <template #action-data="{ row }">
            <NuxtLink :to="`/app/kpi/${row.user_id}`" class="text-crystal-500 hover:text-crystal-700 text-sm">
              查看详情 →
            </NuxtLink>
          </template>
        </UTable>
      </div>

      <!-- Empty state -->
      <div v-if="data.developers.length === 0" class="text-center py-12 text-gray-400">
        暂无数据，请点击"刷新数据"按钮计算 KPI
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
const { api } = useApi()
const toast = useToast()
const router = useRouter()

interface TeamData {
  summary: {
    active_count: number
    resolved_count: number
    avg_resolution_hours: number
    avg_overall_score: number
  }
  developers: Array<{
    user_id: string
    user_name: string
    avatar: string
    scores: Record<string, number>
    rankings: Record<string, number>
  }>
}

const loading = ref(true)
const refreshing = ref(false)
const data = ref<TeamData | null>(null)

const activePeriod = ref('month')
const customStart = ref('')
const customEnd = ref('')
const selectedRole = ref('开发者')

const periodOptions = [
  { label: '本周', value: 'week' },
  { label: '本月', value: 'month' },
  { label: '本季度', value: 'quarter' },
]

const roleOptions = ['全部', '开发者', '测试', '产品经理', '管理员']

const columns = [
  { key: 'rank', label: '排名', sortable: false },
  { key: 'user', label: '开发者', sortable: false },
  { key: 'overall', label: '综合分', sortable: true },
  { key: 'efficiency', label: '效率', sortable: true },
  { key: 'output', label: '产出', sortable: true },
  { key: 'quality', label: '质量', sortable: true },
  { key: 'capability', label: '能力', sortable: true },
  { key: 'growth', label: '成长', sortable: true },
  { key: 'trend', label: '趋势', sortable: false },
  { key: 'action', label: '', sortable: false },
]

const tableRows = computed(() =>
  (data.value?.developers ?? []).map((d, i) => ({
    rank: d.rankings?.overall_rank ?? i + 1,
    user_id: d.user_id,
    user_name: d.user_name,
    overall: d.scores?.overall ?? 0,
    efficiency: d.scores?.efficiency ?? 0,
    output: d.scores?.output ?? 0,
    quality: d.scores?.quality ?? 0,
    capability: d.scores?.capability ?? 0,
    growth: d.scores?.growth ?? 0,
    trend: d.rankings?.growth_percentile ? d.rankings.growth_percentile - 50 : 0,
  }))
)

function scoreColor(score: number) {
  if (score >= 80) return 'text-emerald-600 dark:text-emerald-400'
  if (score >= 60) return 'text-blue-600 dark:text-blue-400'
  if (score >= 40) return 'text-amber-600 dark:text-amber-400'
  return 'text-red-600 dark:text-red-400'
}

function buildQuery() {
  const params = new URLSearchParams()
  if (customStart.value && customEnd.value) {
    params.set('start', customStart.value)
    params.set('end', customEnd.value)
  } else {
    params.set('period', activePeriod.value)
  }
  if (selectedRole.value && selectedRole.value !== '全部') {
    params.set('role', selectedRole.value)
  }
  return params.toString()
}

async function fetchData() {
  loading.value = true
  try {
    data.value = await api<TeamData>(`/api/kpi/team/?${buildQuery()}`)
  } catch (e: any) {
    const detail = e?.data?.detail || e?.response?._data?.detail || '加载失败'
    toast.add({ title: detail, color: 'error' })
  } finally {
    loading.value = false
  }
}

function setPeriod(p: string) {
  activePeriod.value = p
  customStart.value = ''
  customEnd.value = ''
  fetchData()
}

function applyCustom() {
  if (customStart.value && customEnd.value) {
    activePeriod.value = ''
    fetchData()
  }
}

async function refreshData() {
  refreshing.value = true
  try {
    const body: Record<string, string> = {}
    if (customStart.value && customEnd.value) {
      body.start = customStart.value
      body.end = customEnd.value
    }
    if (selectedRole.value && selectedRole.value !== '全部') {
      body.role = selectedRole.value
    }
    await api('/api/kpi/refresh/', { method: 'POST', body })
    toast.add({ title: 'KPI 数据已刷新', color: 'success' })
    await fetchData()
  } catch (e: any) {
    const detail = e?.data?.detail || '刷新失败'
    toast.add({ title: detail, color: 'error' })
  } finally {
    refreshing.value = false
  }
}

function goToProfile(row: any) {
  router.push(`/app/kpi/${row.user_id}`)
}

// Watch role changes
watch(selectedRole, () => fetchData())

onMounted(() => fetchData())
</script>
```

- [ ] **Step 3: Verify dev server starts**

```bash
cd frontend && npm run dev
```

Open browser and navigate to `http://localhost:3004/app/kpi`. Verify the page loads with the toolbar and empty state message.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/pages/app/kpi/index.vue frontend/app/composables/useNavigation.ts
git commit -m "feat(kpi): add team dashboard frontend page"
```

---

## Task 10: Frontend — Personal KPI Profile Page

**Files:**
- Create: `frontend/app/pages/app/kpi/[id].vue`

- [ ] **Step 1: Create the personal KPI profile page with all 4 tabs**

Create `frontend/app/pages/app/kpi/[id].vue`:

```vue
<template>
  <div class="space-y-6">
    <!-- Back button -->
    <UButton
      icon="i-heroicons-arrow-left"
      label="返回"
      variant="ghost"
      size="sm"
      @click="$router.push('/app/kpi')"
    />

    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="text-sm text-gray-400">加载中...</div>
    </div>

    <template v-else-if="summary">
      <!-- User header -->
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-full bg-crystal-100 dark:bg-crystal-900 flex items-center justify-center text-xl font-bold text-crystal-600">
            {{ summary.user_name?.charAt(0)?.toUpperCase() }}
          </div>
          <div class="flex-1">
            <h2 class="text-xl font-bold text-gray-900 dark:text-gray-100">{{ summary.user_name }}</h2>
            <div class="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-2 mt-0.5">
              <span v-for="g in summary.groups" :key="g" class="bg-crystal-50 dark:bg-crystal-950 text-crystal-600 dark:text-crystal-400 px-2 py-0.5 rounded text-xs">{{ g }}</span>
            </div>
          </div>
          <div class="text-right">
            <div class="text-4xl font-bold" :class="scoreColor(summary.scores?.overall)">{{ summary.scores?.overall }}</div>
            <div class="text-xs text-gray-500">综合评分</div>
          </div>
        </div>
      </div>

      <!-- Period selector -->
      <div class="flex items-center gap-2">
        <UButtonGroup>
          <UButton v-for="p in periodOptions" :key="p.value" :label="p.label" :variant="activePeriod === p.value ? 'solid' : 'outline'" size="sm" @click="setPeriod(p.value)" />
        </UButtonGroup>
        <UPopover>
          <UButton icon="i-heroicons-calendar" size="sm" variant="outline" label="自定义" />
          <template #panel>
            <div class="p-3 space-y-2">
              <input type="date" v-model="customStart" class="block w-full rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm" />
              <input type="date" v-model="customEnd" class="block w-full rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm" />
              <UButton label="应用" size="xs" block @click="applyCustom" />
            </div>
          </template>
        </UPopover>
      </div>

      <!-- Tabs -->
      <UTabs :items="tabs" v-model="activeTab">
        <!-- Tab 1: Issue Metrics -->
        <template #issues>
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4">
            <!-- Radar chart -->
            <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">五维评分</h3>
              <ChartsRadarChart
                :labels="['效率', '产出', '质量', '能力', '成长']"
                :datasets="[{
                  label: summary.user_name,
                  data: [summary.scores?.efficiency, summary.scores?.output, summary.scores?.quality, summary.scores?.capability, summary.scores?.growth],
                }]"
                :height="280"
              />
            </div>
            <!-- Issue metric cards -->
            <div class="space-y-3">
              <div v-for="card in issueCards" :key="card.label" class="rounded-xl border p-4 flex justify-between items-center" :class="card.bgClass">
                <span class="text-sm text-gray-600 dark:text-gray-300">{{ card.label }}</span>
                <span class="text-lg font-bold" :class="card.textClass">{{ card.value }}</span>
              </div>
            </div>
          </div>
          <!-- Priority breakdown table -->
          <div v-if="issueData?.priority_breakdown" class="mt-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">按优先级分解</h3>
            <UTable :rows="priorityRows" :columns="priorityColumns" />
          </div>
        </template>

        <!-- Tab 2: Commit Analysis -->
        <template #commits>
          <div v-if="commitData" class="space-y-6 mt-4">
            <!-- Basic stats -->
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4 text-center">
                <div class="text-xs text-gray-500">提交总数</div>
                <div class="text-xl font-bold text-gray-900 dark:text-gray-100 mt-1">{{ commitData.total_commits }}</div>
              </div>
              <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4 text-center">
                <div class="text-xs text-gray-500">代码增删量</div>
                <div class="text-xl font-bold mt-1">
                  <span class="text-emerald-500">+{{ commitData.additions }}</span>
                  <span class="text-red-500 ml-1">-{{ commitData.deletions }}</span>
                </div>
              </div>
              <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4 text-center">
                <div class="text-xs text-gray-500">自引入 Bug 率</div>
                <div class="text-xl font-bold mt-1" :class="commitData.self_introduced_bug_rate > 0.1 ? 'text-red-500' : 'text-emerald-500'">
                  {{ Math.round(commitData.self_introduced_bug_rate * 100) }}%
                </div>
              </div>
              <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4 text-center">
                <div class="text-xs text-gray-500">代码流失率</div>
                <div class="text-xl font-bold mt-1" :class="commitData.churn_rate > 0.2 ? 'text-red-500' : 'text-emerald-500'">
                  {{ Math.round(commitData.churn_rate * 100) }}%
                </div>
              </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <!-- Commit type pie chart -->
              <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">提交类型分布</h3>
                <ChartsPieChart
                  :labels="Object.keys(commitData.commit_type_distribution || {})"
                  :data="Object.values(commitData.commit_type_distribution || {})"
                  :height="240"
                />
              </div>

              <!-- Commit size distribution -->
              <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">提交粒度</h3>
                <div class="text-sm text-gray-500 mb-2">平均每次提交 {{ commitData.avg_commit_size }} 行</div>
                <ChartsBarChart
                  :labels="['小 (<50行)', '中 (50-200行)', '大 (>200行)']"
                  :data="[commitData.commit_size_distribution?.small, commitData.commit_size_distribution?.medium, commitData.commit_size_distribution?.large]"
                  :height="200"
                />
              </div>
            </div>

            <!-- Tech stack breadth -->
            <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">技术栈广度</h3>
              <div class="flex flex-wrap gap-2">
                <span v-for="ext in commitData.file_type_breadth" :key="ext" class="bg-gray-100 dark:bg-gray-800 px-3 py-1 rounded-full text-sm">{{ ext }}</span>
              </div>
            </div>

            <!-- Work rhythm heatmap (simplified as bar charts) -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">工作时段分布</h3>
                <ChartsBarChart
                  :labels="Array.from({length: 24}, (_, i) => `${i}时`)"
                  :data="commitData.work_rhythm?.by_hour"
                  :height="180"
                />
              </div>
              <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">工作日分布</h3>
                <ChartsBarChart
                  :labels="['周一', '周二', '周三', '周四', '周五', '周六', '周日']"
                  :data="commitData.work_rhythm?.by_weekday"
                  :height="180"
                />
              </div>
            </div>

            <!-- Repo coverage -->
            <div v-if="commitData.repo_coverage?.length" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">仓库覆盖</h3>
              <div class="space-y-2">
                <div v-for="r in commitData.repo_coverage" :key="r.repo_id" class="flex justify-between text-sm">
                  <span class="text-gray-700 dark:text-gray-300">{{ r.repo_name }}</span>
                  <span class="text-gray-500">{{ r.commits }} commits</span>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-12 text-gray-400">暂无 Commit 数据</div>
        </template>

        <!-- Tab 3: Trends -->
        <template #trends>
          <div v-if="trendsData?.history?.length" class="space-y-6 mt-4">
            <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">五维评分趋势</h3>
              <ChartsLineChart
                :x-data="trendsData.history.map((h: any) => h.period_end)"
                :series="[
                  { name: '效率', data: trendsData.history.map((h: any) => h.scores?.efficiency ?? 0) },
                  { name: '产出', data: trendsData.history.map((h: any) => h.scores?.output ?? 0) },
                  { name: '质量', data: trendsData.history.map((h: any) => h.scores?.quality ?? 0) },
                  { name: '能力', data: trendsData.history.map((h: any) => h.scores?.capability ?? 0) },
                  { name: '成长', data: trendsData.history.map((h: any) => h.scores?.growth ?? 0) },
                ]"
                :height="320"
              />
            </div>
          </div>
          <div v-else class="text-center py-12 text-gray-400">暂无趋势数据（需要至少 2 个周期的数据）</div>
        </template>

        <!-- Tab 4: Suggestions -->
        <template #suggestions>
          <div v-if="suggestionsData" class="space-y-6 mt-4">
            <!-- Profile -->
            <div class="bg-gradient-to-r from-crystal-50 to-purple-50 dark:from-crystal-950 dark:to-purple-950 rounded-xl p-6 text-center">
              <div class="text-lg font-bold text-gray-900 dark:text-gray-100">{{ suggestionsData.profile }}</div>
              <div class="text-xs text-gray-500 mt-1">能力画像</div>
            </div>

            <!-- Shortcomings -->
            <div v-if="suggestionsData.shortcomings?.length" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">改进建议</h3>
              <div class="space-y-3">
                <div v-for="(s, i) in suggestionsData.shortcomings" :key="i" class="flex items-start gap-3 p-3 rounded-lg" :class="{
                  'bg-red-50 dark:bg-red-950': s.severity === 'high',
                  'bg-amber-50 dark:bg-amber-950': s.severity === 'medium',
                  'bg-gray-50 dark:bg-gray-800': s.severity === 'low',
                }">
                  <span class="text-xs font-mono px-1.5 py-0.5 rounded" :class="{
                    'bg-red-200 text-red-800 dark:bg-red-900 dark:text-red-200': s.severity === 'high',
                    'bg-amber-200 text-amber-800 dark:bg-amber-900 dark:text-amber-200': s.severity === 'medium',
                    'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300': s.severity === 'low',
                  }">{{ s.severity }}</span>
                  <span class="text-sm text-gray-700 dark:text-gray-300">{{ s.message }}</span>
                </div>
              </div>
            </div>

            <!-- Trends -->
            <div v-if="suggestionsData.trends?.length" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-5">
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">趋势变化</h3>
              <div class="space-y-2">
                <div v-for="(t, i) in suggestionsData.trends" :key="i" class="text-sm p-2 rounded" :class="{
                  'text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950': t.direction === 'up',
                  'text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-950': t.direction === 'down',
                }">
                  {{ t.message }}
                </div>
              </div>
            </div>

            <div v-if="!suggestionsData.shortcomings?.length && !suggestionsData.trends?.length" class="text-center py-8 text-gray-400">
              各维度表现良好，暂无改进建议
            </div>
          </div>
          <div v-else class="text-center py-12 text-gray-400">暂无数据</div>
        </template>
      </UTabs>
    </template>

    <!-- No data state -->
    <div v-else-if="!loading" class="text-center py-20 text-gray-400">
      暂无 KPI 数据，请先在团队仪表盘刷新数据
    </div>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const { api } = useApi()
const { user: currentUser } = useAuth()
const toast = useToast()

const userId = computed(() => {
  const id = route.params.id as string
  return id === 'me' ? currentUser.value?.id : id
})

const loading = ref(true)
const summary = ref<any>(null)
const issueData = ref<any>(null)
const commitData = ref<any>(null)
const trendsData = ref<any>(null)
const suggestionsData = ref<any>(null)
const activeTab = ref(0)

const activePeriod = ref('month')
const customStart = ref('')
const customEnd = ref('')

const periodOptions = [
  { label: '本周', value: 'week' },
  { label: '本月', value: 'month' },
  { label: '本季度', value: 'quarter' },
]

const tabs = [
  { label: '问题指标', slot: 'issues' },
  { label: 'Commit 分析', slot: 'commits' },
  { label: '趋势变化', slot: 'trends' },
  { label: '改进建议', slot: 'suggestions' },
]

const issueCards = computed(() => {
  const d = issueData.value
  if (!d) return []
  return [
    { label: '负责问题数', value: d.assigned_count, bgClass: 'bg-emerald-50 dark:bg-emerald-950 border-emerald-200 dark:border-emerald-800', textClass: 'text-emerald-600' },
    { label: '已解决', value: `${d.resolved_count} (${Math.round(d.resolution_rate * 100)}%)`, bgClass: 'bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800', textClass: 'text-blue-600' },
    { label: '平均解决耗时', value: `${d.avg_resolution_hours}h`, bgClass: 'bg-amber-50 dark:bg-amber-950 border-amber-200 dark:border-amber-800', textClass: 'text-amber-600' },
    { label: '日均解决', value: `${d.daily_resolved_avg} 个`, bgClass: 'bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800', textClass: 'text-purple-600' },
    { label: '加权问题价值', value: `${d.weighted_issue_value} 分`, bgClass: 'bg-orange-50 dark:bg-orange-950 border-orange-200 dark:border-orange-800', textClass: 'text-orange-600' },
  ]
})

const priorityColumns = [
  { key: 'priority', label: '优先级' },
  { key: 'assigned', label: '负责数' },
  { key: 'resolved', label: '已解决' },
  { key: 'avg_hours', label: '平均耗时' },
]

const priorityRows = computed(() => {
  const pb = issueData.value?.priority_breakdown
  if (!pb) return []
  return Object.entries(pb).map(([prio, data]: [string, any]) => ({
    priority: prio,
    assigned: data.assigned,
    resolved: data.resolved,
    avg_hours: `${data.avg_hours}h`,
  }))
})

function scoreColor(score: number) {
  if (score >= 80) return 'text-emerald-600 dark:text-emerald-400'
  if (score >= 60) return 'text-blue-600 dark:text-blue-400'
  if (score >= 40) return 'text-amber-600 dark:text-amber-400'
  return 'text-red-600 dark:text-red-400'
}

function buildQuery() {
  const params = new URLSearchParams()
  if (customStart.value && customEnd.value) {
    params.set('start', customStart.value)
    params.set('end', customEnd.value)
  } else {
    params.set('period', activePeriod.value)
  }
  return params.toString()
}

async function fetchAll() {
  loading.value = true
  const uid = userId.value
  if (!uid) return
  const q = buildQuery()
  try {
    const [s, i, c, t, sg] = await Promise.all([
      api<any>(`/api/kpi/users/${uid}/summary/?${q}`),
      api<any>(`/api/kpi/users/${uid}/issues/?${q}`),
      api<any>(`/api/kpi/users/${uid}/commits/?${q}`),
      api<any>(`/api/kpi/users/${uid}/trends/?periods=6`),
      api<any>(`/api/kpi/users/${uid}/suggestions/?${q}`),
    ])
    summary.value = s
    issueData.value = i
    commitData.value = c
    trendsData.value = t
    suggestionsData.value = sg
  } catch (e: any) {
    const detail = e?.data?.detail || e?.response?._data?.detail || '加载失败'
    if (e?.response?.status !== 404) {
      toast.add({ title: detail, color: 'error' })
    }
  } finally {
    loading.value = false
  }
}

function setPeriod(p: string) {
  activePeriod.value = p
  customStart.value = ''
  customEnd.value = ''
  fetchAll()
}

function applyCustom() {
  if (customStart.value && customEnd.value) {
    activePeriod.value = ''
    fetchAll()
  }
}

onMounted(() => fetchAll())
</script>
```

- [ ] **Step 2: Check if ChartsBarChart component exists**

The page uses `ChartsBarChart` which may not exist yet. Check `frontend/app/components/Charts/` for available chart components. If `BarChart.vue` doesn't exist, create it following the pattern of existing chart components (e.g., `LineChart.vue` or `PieChart.vue`). This is a simple Chart.js bar chart wrapper.

- [ ] **Step 3: Verify the page loads in browser**

```bash
cd frontend && npm run dev
```

Navigate to `http://localhost:3004/app/kpi/{some-user-id}` and verify the page structure loads (even if data shows "暂无数据").

- [ ] **Step 4: Commit**

```bash
git add frontend/app/pages/app/kpi/
git commit -m "feat(kpi): add personal KPI profile page with 4 tabs"
```

---

## Task 11: ChartsBarChart Component (if needed)

**Files:**
- Create: `frontend/app/components/Charts/BarChart.vue` (only if it doesn't exist)

- [ ] **Step 1: Check if BarChart component exists**

```bash
ls frontend/app/components/Charts/
```

If `BarChart.vue` does NOT exist, create it.

- [ ] **Step 2: Create BarChart component (skip if already exists)**

Create `frontend/app/components/Charts/BarChart.vue` following the same pattern as existing chart components in that directory. It should accept `labels` (string array), `data` (number array), and `height` (number) props and render a Chart.js bar chart.

- [ ] **Step 3: Commit (only if created)**

```bash
git add frontend/app/components/Charts/BarChart.vue
git commit -m "feat(kpi): add BarChart component for commit analysis"
```

---

## Task 12: End-to-End Verification

**Files:** None (testing only)

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && uv run pytest tests/test_kpi_metrics.py tests/test_kpi_scoring.py tests/test_kpi_suggestions.py tests/test_kpi_api.py -v
```

Expected: All tests PASS

- [ ] **Step 2: Run backend server and verify API**

```bash
cd backend && uv run python manage.py runserver
```

Test endpoints with curl:
```bash
# Should return 200 (empty data)
curl -s http://localhost:8000/api/kpi/team/ -H "Authorization: Bearer <token>" | python -m json.tool
```

- [ ] **Step 3: Run frontend and verify pages**

```bash
cd frontend && npm run dev
```

1. Navigate to `/app/kpi` — verify team dashboard loads
2. Click "刷新数据" — verify KPI computation runs
3. Click a developer row — verify personal profile loads with 4 tabs
4. Check sidebar — verify "KPI 分析" appears under "用户管理"

- [ ] **Step 4: Run frontend type check**

```bash
cd frontend && npx nuxi typecheck
```

Fix any TypeScript errors.

- [ ] **Step 5: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix(kpi): address issues found during e2e verification"
```
