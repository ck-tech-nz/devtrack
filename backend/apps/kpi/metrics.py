"""
KPI 指标计算模块

compute_issue_metrics  — 问题指标
compute_commit_metrics — Commit 指标
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime

from django.utils import timezone

from apps.issues.models import Issue
from apps.repos.models import Commit, GitAuthorAlias

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

RESOLVED_STATUSES = {"已解决", "已关闭"}

PRIORITY_WEIGHTS = {"P0": 4, "P1": 3, "P2": 2, "P3": 1}

CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|refactor|chore|docs|style|test|perf|ci|build)(\(.+\))?[!]?:\s.+"
)

# ---------------------------------------------------------------------------
# 问题指标
# ---------------------------------------------------------------------------


def compute_issue_metrics(
    user, period_start: date, period_end: date
) -> dict:
    """计算指定用户在 [period_start, period_end] 内的问题指标。"""

    start_dt = timezone.make_aware(datetime.combine(period_start, datetime.min.time()))
    end_dt = timezone.make_aware(datetime.combine(period_end, datetime.max.time()))

    # 分配给该用户且在时间范围内创建的 Issues
    assigned_qs = Issue.objects.filter(
        assignee=user,
        created_at__gte=start_dt,
        created_at__lte=end_dt,
    )

    assigned_count = assigned_qs.count()

    if assigned_count == 0:
        return _empty_issue_metrics()

    resolved_qs = assigned_qs.filter(status__in=RESOLVED_STATUSES)
    resolved_count = resolved_qs.count()
    resolution_rate = round(resolved_count / assigned_count, 4) if assigned_count else 0

    # 平均解决时间（小时）
    resolved_with_time = resolved_qs.filter(resolved_at__isnull=False)
    if resolved_with_time.exists():
        total_hours = sum(
            (issue.resolved_at - issue.created_at).total_seconds() / 3600
            for issue in resolved_with_time
        )
        avg_resolution_hours = round(total_hours / resolved_with_time.count(), 2)
    else:
        avg_resolution_hours = 0

    # 每日 / 每周平均解决量
    period_days = max((period_end - period_start).days, 1)
    daily_resolved_avg = round(resolved_count / period_days, 4)
    weekly_resolved_avg = round(daily_resolved_avg * 7, 4)

    # 按优先级拆分
    priority_breakdown = {}
    for prio in ("P0", "P1", "P2", "P3"):
        prio_qs = assigned_qs.filter(priority=prio)
        prio_assigned = prio_qs.count()
        prio_resolved_qs = prio_qs.filter(status__in=RESOLVED_STATUSES, resolved_at__isnull=False)
        prio_resolved = prio_resolved_qs.count()

        if prio_resolved:
            prio_hours = sum(
                (i.resolved_at - i.created_at).total_seconds() / 3600
                for i in prio_resolved_qs
            )
            prio_avg_hours = round(prio_hours / prio_resolved, 2)
        else:
            prio_avg_hours = 0

        priority_breakdown[prio] = {
            "assigned": prio_assigned,
            "resolved": prio_resolved,
            "avg_hours": prio_avg_hours,
        }

    # 加权 Issue 价值
    weighted_issue_value = 0
    for issue in resolved_with_time:
        resolution_hours = (issue.resolved_at - issue.created_at).total_seconds() / 3600
        helper_count = issue.helpers.count()
        activity_count = issue.activities.count()

        complexity_signal = (
            resolution_hours * 0.4
            + helper_count * 0.3
            + activity_count * 0.3
        )
        priority_weight = PRIORITY_WEIGHTS.get(issue.priority, 1)
        weighted_issue_value += priority_weight * complexity_signal

    weighted_issue_value = round(weighted_issue_value, 4)

    # 作为协助人参与（不是负责人）
    as_helper_count = (
        Issue.objects.filter(
            helpers=user,
            created_at__gte=start_dt,
            created_at__lte=end_dt,
        )
        .exclude(assignee=user)
        .distinct()
        .count()
    )

    return {
        "assigned_count": assigned_count,
        "resolved_count": resolved_count,
        "resolution_rate": resolution_rate,
        "avg_resolution_hours": avg_resolution_hours,
        "daily_resolved_avg": daily_resolved_avg,
        "weekly_resolved_avg": weekly_resolved_avg,
        "priority_breakdown": priority_breakdown,
        "weighted_issue_value": weighted_issue_value,
        "as_helper_count": as_helper_count,
    }


def _empty_issue_metrics() -> dict:
    return {
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


# ---------------------------------------------------------------------------
# Commit 指标
# ---------------------------------------------------------------------------


def compute_commit_metrics(
    user, period_start: date, period_end: date
) -> dict:
    """计算指定用户在 [period_start, period_end] 内的 Commit 指标。"""

    start_dt = timezone.make_aware(datetime.combine(period_start, datetime.min.time()))
    end_dt = timezone.make_aware(datetime.combine(period_end, datetime.max.time()))

    # 通过 GitAuthorAlias 找到用户的所有邮箱
    author_emails = set(
        GitAuthorAlias.objects.filter(user=user).values_list("author_email", flat=True)
    )

    if not author_emails:
        return _empty_commit_metrics()

    commits_qs = Commit.objects.filter(
        author_email__in=author_emails,
        date__gte=start_dt,
        date__lte=end_dt,
    )

    commits = list(commits_qs.order_by("date"))
    total_commits = len(commits)

    if total_commits == 0:
        return _empty_commit_metrics()

    # 基础统计
    total_additions = sum(c.additions for c in commits)
    total_deletions = sum(c.deletions for c in commits)
    lines_changed = total_additions + total_deletions

    # Commit 大小分布
    small = medium = large = 0
    for c in commits:
        size = c.additions + c.deletions
        if size < 50:
            small += 1
        elif size <= 200:
            medium += 1
        else:
            large += 1

    commit_size_distribution = {"small": small, "medium": medium, "large": large}
    avg_commit_size = round(lines_changed / total_commits, 2) if total_commits else 0

    # 文件类型广度
    extensions = set()
    for c in commits:
        for f in c.files_changed or []:
            if "." in f:
                ext = f.rsplit(".", 1)[-1]
                extensions.add(ext)
    file_type_breadth = len(extensions)

    # 工作节奏
    by_hour = [0] * 24
    by_weekday = [0] * 7
    for c in commits:
        local_dt = timezone.localtime(c.date)
        by_hour[local_dt.hour] += 1
        by_weekday[local_dt.weekday()] += 1

    work_rhythm = {"by_hour": by_hour, "by_weekday": by_weekday}

    # Conventional commit 分析
    conventional_count = 0
    type_counts: dict[str, int] = defaultdict(int)
    refactor_count = 0
    for c in commits:
        first_line = c.message.split("\n", 1)[0]
        m = CONVENTIONAL_RE.match(first_line)
        if m:
            conventional_count += 1
            ctype = m.group(1)
            type_counts[ctype] += 1
            if ctype == "refactor":
                refactor_count += 1

    conventional_ratio = round(conventional_count / total_commits, 4)
    refactor_ratio = round(refactor_count / total_commits, 4)
    commit_type_distribution = dict(type_counts)

    # Self-introduced bug rate
    # feat/refactor commit 之后 72 小时内同一作者在相同文件上提交 fix
    feat_refactor_commits = [
        c for c in commits
        if CONVENTIONAL_RE.match(c.message.split("\n", 1)[0])
        and CONVENTIONAL_RE.match(c.message.split("\n", 1)[0]).group(1) in ("feat", "refactor")
    ]

    fix_commits = [
        c for c in commits
        if CONVENTIONAL_RE.match(c.message.split("\n", 1)[0])
        and CONVENTIONAL_RE.match(c.message.split("\n", 1)[0]).group(1) == "fix"
    ]

    self_bug_count = 0
    for fc in feat_refactor_commits:
        fc_files = set(fc.files_changed or [])
        for fix_c in fix_commits:
            if fix_c.date <= fc.date:
                continue
            time_diff = (fix_c.date - fc.date).total_seconds()
            if time_diff > 72 * 3600:
                continue
            fix_files = set(fix_c.files_changed or [])
            if fc_files & fix_files:
                self_bug_count += 1
                break  # 每个 feat/refactor 只计一次

    fr_count = len(feat_refactor_commits)
    self_introduced_bug_rate = round(self_bug_count / fr_count, 4) if fr_count else 0

    # Churn rate — 30 天内同一文件再次修改的比例
    file_modify_dates: dict[str, list[datetime]] = defaultdict(list)
    for c in commits:
        for f in c.files_changed or []:
            file_modify_dates[f].append(c.date)

    churn_files = 0
    total_file_touches = 0
    for f, dates in file_modify_dates.items():
        dates_sorted = sorted(dates)
        total_file_touches += len(dates_sorted)
        for i in range(1, len(dates_sorted)):
            if (dates_sorted[i] - dates_sorted[i - 1]).days <= 30:
                churn_files += 1

    churn_rate = round(churn_files / total_file_touches, 4) if total_file_touches else 0

    # Repo 覆盖
    repo_map: dict[int, dict] = {}
    for c in commits:
        if c.repo_id not in repo_map:
            repo_map[c.repo_id] = {"repo_id": c.repo_id, "repo_name": c.repo.name, "commits": 0}
        repo_map[c.repo_id]["commits"] += 1
    repo_coverage = list(repo_map.values())

    return {
        "total_commits": total_commits,
        "additions": total_additions,
        "deletions": total_deletions,
        "lines_changed": lines_changed,
        "self_introduced_bug_rate": self_introduced_bug_rate,
        "churn_rate": churn_rate,
        "commit_size_distribution": commit_size_distribution,
        "avg_commit_size": avg_commit_size,
        "file_type_breadth": file_type_breadth,
        "work_rhythm": work_rhythm,
        "refactor_ratio": refactor_ratio,
        "commit_type_distribution": commit_type_distribution,
        "conventional_ratio": conventional_ratio,
        "repo_coverage": repo_coverage,
    }


def _empty_commit_metrics() -> dict:
    return {
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
