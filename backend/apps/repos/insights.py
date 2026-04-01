import math
import re
from collections import defaultdict
from datetime import timedelta

from django.utils import timezone

from apps.repos.models import Commit, GitAuthorAlias

# 规范提交消息的完整匹配正则
_CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|refactor|chore|docs|style|test|perf|ci|build)(\(.+\))?[!]?:\s.+"
)
# 提取提交类型的前缀正则
_TYPE_RE = re.compile(
    r"^(feat|fix|refactor|chore|docs|style|test|perf|ci|build)"
)


class DeveloperInsightsService:
    """计算开发者四维评分（贡献量、效率、能力、质量）的服务类。"""

    # ------------------------------------------------------------------
    # 公共方法
    # ------------------------------------------------------------------

    def team_overview(self, repo, days=90):
        """
        返回仓库内所有开发者的概览列表，包含四维评分和基础统计数据。
        结果按 commit_count 降序排列。
        """
        aliases = GitAuthorAlias.objects.filter(repo=repo).select_related("user")
        cutoff = self._cutoff(days)

        # 为每位开发者计算原始指标
        raw_metrics = {}
        for alias in aliases:
            qs = Commit.objects.filter(repo=repo, author_email=alias.author_email)
            if cutoff:
                qs = qs.filter(date__gte=cutoff)
            raw_metrics[alias.author_email] = self._compute_raw_metrics(qs, days)

        results = []
        for alias in aliases:
            email = alias.author_email
            metrics = raw_metrics[email]
            scores = self._percentile_scores(email, raw_metrics)
            results.append(
                {
                    "alias_id": alias.id,
                    "author_email": email,
                    "author_name": alias.author_name,
                    "user_id": alias.user_id,
                    "user_name": alias.user.name if alias.user else None,
                    "scores": scores,
                    "stats": {
                        "commit_count": metrics["commit_count"],
                        "additions": metrics["additions"],
                        "deletions": metrics["deletions"],
                    },
                }
            )

        results.sort(key=lambda x: x["stats"]["commit_count"], reverse=True)
        return results

    def individual_detail(self, repo, alias_id, days=90):
        """
        返回单个开发者的详细信息，在 team_overview 条目基础上
        新增 details 字段（含所有原始指标）。
        """
        alias = GitAuthorAlias.objects.select_related("user").get(id=alias_id, repo=repo)
        cutoff = self._cutoff(days)

        # 目标开发者的指标
        target_qs = Commit.objects.filter(repo=repo, author_email=alias.author_email)
        if cutoff:
            target_qs = target_qs.filter(date__gte=cutoff)
        target_metrics = self._compute_raw_metrics(target_qs, days)

        # 团队所有成员的原始指标（用于百分位排名）
        aliases = GitAuthorAlias.objects.filter(repo=repo)
        raw_metrics = {}
        for a in aliases:
            qs = Commit.objects.filter(repo=repo, author_email=a.author_email)
            if cutoff:
                qs = qs.filter(date__gte=cutoff)
            raw_metrics[a.author_email] = self._compute_raw_metrics(qs, days)

        scores = self._percentile_scores(alias.author_email, raw_metrics)

        return {
            "alias_id": alias.id,
            "author_email": alias.author_email,
            "author_name": alias.author_name,
            "user_id": alias.user_id,
            "user_name": alias.user.name if alias.user else None,
            "scores": scores,
            "stats": {
                "commit_count": target_metrics["commit_count"],
                "additions": target_metrics["additions"],
                "deletions": target_metrics["deletions"],
            },
            "details": {
                "commit_count": target_metrics["commit_count"],
                "additions": target_metrics["additions"],
                "deletions": target_metrics["deletions"],
                "commit_frequency": target_metrics["commit_frequency"],
                "active_days_ratio": target_metrics["active_days_ratio"],
                "directory_count": target_metrics["directory_count"],
                "commit_types": target_metrics["commit_types"],
                "fix_ratio": target_metrics["fix_ratio"],
                "conventional_ratio": target_metrics["conventional_ratio"],
            },
        }

    def unlinked_authors(self, repo):
        """
        返回未关联系统用户的 Git 作者列表。
        """
        aliases = GitAuthorAlias.objects.filter(repo=repo, user__isnull=True)
        return [
            {
                "id": a.id,
                "author_email": a.author_email,
                "author_name": a.author_name,
            }
            for a in aliases
        ]

    # ------------------------------------------------------------------
    # 私有辅助方法
    # ------------------------------------------------------------------

    def _cutoff(self, days):
        """根据 days 参数返回截止时间，days 为 None 或 0 时返回 None。"""
        if not days:
            return None
        return timezone.now() - timedelta(days=days)

    def _compute_raw_metrics(self, commits_qs, days):
        """
        计算单个开发者的所有原始指标。
        commits_qs 已经过时间范围过滤。
        """
        commits = list(commits_qs.values("date", "message", "additions", "deletions", "files_changed"))

        if not commits:
            return self._empty_metrics()

        commit_count = len(commits)
        additions = sum(c["additions"] for c in commits)
        deletions = sum(c["deletions"] for c in commits)

        # 活跃天数比率：活跃天数 / 时间窗口天数
        active_dates = {c["date"].date() for c in commits}
        active_days = len(active_dates)
        window_days = days if days else 1
        active_days_ratio = active_days / window_days

        # 提交频率：每周提交次数
        commit_frequency = commit_count / (window_days / 7)

        # 唯一顶层目录数量
        dirs = set()
        for c in commits:
            for path in (c["files_changed"] or []):
                parts = path.split("/")
                dirs.add(parts[0] if len(parts) > 1 else ".")
        directory_count = len(dirs)

        # 提交类型分布与规范提交比率
        commit_types: dict[str, int] = defaultdict(int)
        conventional_count = 0
        for c in commits:
            msg = (c["message"] or "").strip().split("\n")[0]
            if _CONVENTIONAL_RE.match(msg):
                conventional_count += 1
            m = _TYPE_RE.match(msg)
            if m:
                commit_types[m.group(1)] += 1

        conventional_ratio = conventional_count / commit_count
        fix_ratio = commit_types.get("fix", 0) / commit_count

        # Shannon 熵（基于提交类型分布）
        type_entropy = self._shannon_entropy(dict(commit_types), commit_count)

        return {
            "commit_count": commit_count,
            "additions": additions,
            "deletions": deletions,
            "lines_changed": additions + deletions,
            "commit_frequency": commit_frequency,
            "active_days_ratio": active_days_ratio,
            "directory_count": directory_count,
            "commit_types": dict(commit_types),
            "type_entropy": type_entropy,
            "fix_ratio": fix_ratio,
            "conventional_ratio": conventional_ratio,
        }

    def _percentile_scores(self, target_email, raw_metrics):
        """
        对目标开发者的四个维度使用百分位排名打分（0–100）。
        团队只有一人时所有维度均为 50。
        """
        n = len(raw_metrics)
        if n <= 1:
            return {"contribution": 50, "efficiency": 50, "capability": 50, "quality": 50}

        target = raw_metrics[target_email]
        all_metrics = list(raw_metrics.values())

        def percentile(key):
            """计算 target 在所有成员中的百分位得分（值越高越好）。"""
            target_val = target[key]
            below = sum(1 for m in all_metrics if m[key] < target_val)
            return round(below / (n - 1) * 100)

        def percentile_inv(key):
            """反向百分位（值越低越好，如 fix_ratio）。"""
            target_val = target[key]
            above = sum(1 for m in all_metrics if m[key] > target_val)
            return round(above / (n - 1) * 100)

        def avg_percentile(key1, key2):
            """两个子指标各取百分位后平均。"""
            return round((percentile(key1) + percentile(key2)) / 2)

        contribution = avg_percentile("commit_count", "lines_changed")
        efficiency = avg_percentile("commit_frequency", "active_days_ratio")
        capability = avg_percentile("directory_count", "type_entropy")
        quality = round((percentile_inv("fix_ratio") + percentile("conventional_ratio")) / 2)

        return {
            "contribution": contribution,
            "efficiency": efficiency,
            "capability": capability,
            "quality": quality,
        }

    @staticmethod
    def _shannon_entropy(type_counts, total):
        """计算提交类型分布的 Shannon 熵。"""
        if total == 0:
            return 0.0
        entropy = 0.0
        for count in type_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        return entropy

    @staticmethod
    def _empty_metrics():
        """返回所有指标均为零的默认字典。"""
        return {
            "commit_count": 0,
            "additions": 0,
            "deletions": 0,
            "lines_changed": 0,
            "commit_frequency": 0.0,
            "active_days_ratio": 0.0,
            "directory_count": 0,
            "commit_types": {},
            "type_entropy": 0.0,
            "fix_ratio": 0.0,
            "conventional_ratio": 0.0,
        }
