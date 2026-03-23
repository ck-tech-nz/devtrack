import hashlib
import json
from datetime import timedelta

from django.db.models import Max, Count, Avg, F, Q
from django.utils import timezone

from apps.issues.models import Issue
from apps.repos.models import GitHubIssue
from .client import LLMClient
from .models import LLMConfig, Prompt, Analysis


class AIConfigurationError(Exception):
    pass


def parse_json_response(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)


def _ts(val):
    return val.isoformat() if val is not None else "1970-01-01T00:00:00+00:00"


class AIAnalysisService:
    def get_or_run(self, analysis_type: str, triggered_by: str, user=None) -> Analysis:
        latest = (
            Analysis.objects.filter(analysis_type=analysis_type, status=Analysis.Status.DONE)
            .order_by("-created_at")
            .first()
        )
        if latest and not self._is_stale(latest):
            return latest
        data_hash = self._compute_data_hash(analysis_type)
        return self._run(analysis_type, triggered_by, user, data_hash=data_hash)

    def _is_stale(self, analysis: Analysis) -> bool:
        if (timezone.now() - analysis.created_at) > timedelta(hours=1):
            return True
        return self._compute_data_hash(analysis.analysis_type) != analysis.data_hash

    def _compute_data_hash(self, analysis_type: str) -> str:
        data = {
            "issue_count": Issue.objects.count(),
            "issue_max_updated": _ts(Issue.objects.aggregate(m=Max("updated_at"))["m"]),
            "github_issue_count": GitHubIssue.objects.count(),
            "github_issue_max_synced": _ts(GitHubIssue.objects.aggregate(m=Max("synced_at"))["m"]),
        }
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def _aggregate_context(self, analysis_type: str) -> dict:
        period = 30
        since = timezone.now() - timedelta(days=period)

        issues_by_priority = dict(
            Issue.objects.values("priority")
            .annotate(count=Count("id"))
            .values_list("priority", "count")
        )

        issues_by_assignee = []
        for row in (
            Issue.objects.filter(assignee__isnull=False)
            .values("assignee__name")
            .annotate(
                open_count=Count("id", filter=~Q(status="已解决")),
                closed_count=Count("id", filter=Q(status="已解决")),
                avg_hours=Avg(F("resolved_at") - F("created_at")),
            )
        ):
            avg = row["avg_hours"]
            issues_by_assignee.append({
                "name": row["assignee__name"],
                "open": row["open_count"],
                "closed": row["closed_count"],
                "avg_hours": round(avg.total_seconds() / 3600, 1) if avg else None,
            })

        from apps.repos.models import Repo
        github_summary = []
        for repo in Repo.objects.all():
            qs = GitHubIssue.objects.filter(repo=repo)
            if not qs.exists():
                continue
            label_counts: dict[str, int] = {}
            for labels in qs.values_list("labels", flat=True):
                for label in labels:
                    label_counts[label] = label_counts.get(label, 0) + 1
            top_labels = sorted(label_counts, key=label_counts.get, reverse=True)[:10]
            github_summary.append({
                "repo": repo.full_name,
                "open": qs.filter(state="open").count(),
                "closed": qs.filter(state="closed").count(),
                "labels": top_labels,
            })

        recent_closed = []
        for issue in Issue.objects.filter(
            resolved_at__gte=since, resolved_at__isnull=False
        ).select_related("assignee")[:50]:
            hours = None
            if issue.resolved_at and issue.created_at:
                hours = round((issue.resolved_at - issue.created_at).total_seconds() / 3600, 1)
            recent_closed.append({
                "title": issue.title,
                "priority": issue.priority,
                "assignee": issue.assignee.name if issue.assignee else "",
                "hours_to_close": hours,
            })

        return {
            "period_days": period,
            "total_issues": Issue.objects.count(),
            "open_issues": Issue.objects.exclude(status="已解决").count(),
            "closed_issues": Issue.objects.filter(status="已解决").count(),
            "issues_by_priority": issues_by_priority,
            "issues_by_assignee": issues_by_assignee,
            "github_issues_summary": github_summary,
            "recent_closed_issues": recent_closed,
        }

    def _run(self, analysis_type: str, triggered_by: str, user=None, data_hash: str = "") -> Analysis:
        template = Prompt.objects.filter(slug=analysis_type, is_active=True).first()
        if not template:
            raise AIConfigurationError(f"No active Prompt for '{analysis_type}'")

        llm_config = template.llm_config
        if llm_config is None:
            llm_config = LLMConfig.objects.filter(is_default=True, is_active=True).first()
        if llm_config is None:
            raise AIConfigurationError("No default LLMConfig configured")

        context = self._aggregate_context(analysis_type)

        try:
            user_prompt = template.user_prompt_template.format(**context)
        except KeyError as e:
            raise AIConfigurationError(f"Prompt template has missing placeholder: {e}")

        analysis = Analysis.objects.create(
            analysis_type=analysis_type,
            prompt_template=template,
            triggered_by=triggered_by,
            triggered_by_user=user if triggered_by == Analysis.TriggerType.MANUAL else None,
            status=Analysis.Status.RUNNING,
            data_hash=data_hash,
            input_context=context,
            prompt_snapshot={
                "system_prompt": template.system_prompt,
                "user_prompt": user_prompt,
                "model": template.llm_model,
                "base_url": llm_config.base_url,
                "temperature": template.temperature,
            },
        )

        try:
            raw = LLMClient(llm_config).complete(
                model=template.llm_model,
                system_prompt=template.system_prompt,
                user_prompt=user_prompt,
                temperature=template.temperature,
            )
            parsed = parse_json_response(raw)
            analysis.raw_response = raw
            analysis.parsed_result = parsed
            analysis.status = Analysis.Status.DONE
            analysis.save(update_fields=["raw_response", "parsed_result", "status", "updated_at"])
        except Exception as e:
            analysis.status = Analysis.Status.FAILED
            analysis.error_message = str(e)
            analysis.save(update_fields=["status", "error_message", "updated_at"])
            raise

        return analysis
