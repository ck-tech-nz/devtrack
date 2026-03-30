import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.db import close_old_connections
from django.db.models import Max, Count, Avg, F, Q
from django.utils import timezone

from apps.issues.models import Issue
from apps.repos.models import GitHubIssue
from .client import LLMClient
from .models import LLMConfig, Prompt, Analysis
from .opencode import OpenCodeRunner


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


logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4)


class IssueAnalysisService:
    ALLOWED_FIELDS = {"cause", "solution", "remark"}

    def analyze(self, issue, triggered_by="manual", user=None):
        if not issue.repo:
            raise ValueError("请先关联仓库")
        if issue.repo.clone_status != "cloned":
            raise ValueError("请先同步代码")

        analysis = Analysis.objects.create(
            analysis_type="issue_code_analysis",
            issue=issue,
            triggered_by=triggered_by,
            triggered_by_user=user if triggered_by == "manual" else None,
            status=Analysis.Status.RUNNING,
        )
        self._execute_analysis(analysis, issue)
        return analysis

    def analyze_async(self, issue, triggered_by="auto", user=None):
        analysis = Analysis.objects.create(
            analysis_type="issue_code_analysis",
            issue=issue,
            triggered_by=triggered_by,
            triggered_by_user=user if triggered_by == "manual" else None,
            status=Analysis.Status.RUNNING,
        )
        _executor.submit(self._run_in_thread, analysis.id, issue.id)
        return analysis

    def _run_in_thread(self, analysis_id, issue_id):
        try:
            issue = Issue.objects.select_related("repo").get(pk=issue_id)
            analysis = Analysis.objects.get(pk=analysis_id)
            self._execute_analysis(analysis, issue)
        except Exception:
            logger.exception("AI analysis thread failed for analysis %s", analysis_id)
            Analysis.objects.filter(pk=analysis_id).update(
                status=Analysis.Status.FAILED,
                error_message="执行异常",
            )
        finally:
            close_old_connections()

    def _execute_analysis(self, analysis, issue):
        prompt_template = Prompt.objects.filter(
            slug="issue_code_analysis", is_active=True
        ).first()
        if not prompt_template:
            analysis.status = Analysis.Status.FAILED
            analysis.error_message = "No active Prompt for 'issue_code_analysis'"
            analysis.save(update_fields=["status", "error_message", "updated_at"])
            return

        llm_config = prompt_template.llm_config or LLMConfig.objects.filter(
            is_default=True, is_active=True
        ).first()
        if not llm_config:
            analysis.status = Analysis.Status.FAILED
            analysis.error_message = "No default LLMConfig configured"
            analysis.save(update_fields=["status", "error_message", "updated_at"])
            return

        try:
            context = {
                "title": issue.title,
                "description": (issue.description or "")[:500],
                "priority": issue.priority,
                "status": issue.status,
                "labels": ", ".join(issue.labels) if issue.labels else "",
                "cause": issue.cause or "",
                "solution": issue.solution or "",
                "remark": issue.remark or "",
            }
            user_prompt = prompt_template.user_prompt_template.format(**context)
            runner = OpenCodeRunner(llm_config)
            # Compose prompt from DB template: system_prompt + user_prompt
            prompt = f"{prompt_template.system_prompt.strip()}\n\n{user_prompt.strip()}"

            raw = runner.run(
                repo_path=issue.repo.local_path,
                prompt=prompt,
                model=prompt_template.llm_model,
            )

            # opencode --format json outputs JSON event lines
            # Extract text content from "type":"text" events
            text_content = self._extract_opencode_text(raw)
            if not text_content:
                raise ValueError("opencode 未返回有效文本内容")

            # Parse response: supports {cause, solution} and legacy {target_field, content}
            try:
                parsed = parse_json_response(text_content)
                if any(k in parsed for k in self.ALLOWED_FIELDS):
                    parsed = {k: v for k, v in parsed.items()
                              if k in self.ALLOWED_FIELDS and v}
                elif "target_field" in parsed and parsed["target_field"] in self.ALLOWED_FIELDS:
                    parsed = {parsed["target_field"]: parsed.get("content", "")}
                else:
                    parsed = {self._guess_target_field(issue): text_content}
            except (json.JSONDecodeError, ValueError):
                parsed = {self._guess_target_field(issue): text_content}

            analysis.raw_response = raw
            analysis.parsed_result = parsed
            analysis.prompt_template = prompt_template
            analysis.status = Analysis.Status.DONE
            analysis.save(update_fields=[
                "raw_response", "parsed_result", "prompt_template",
                "status", "updated_at",
            ])
        except Exception as e:
            analysis.status = Analysis.Status.FAILED
            analysis.error_message = str(e)
            analysis.save(update_fields=["status", "error_message", "updated_at"])

    @staticmethod
    def _guess_target_field(issue):
        """Pick the best field: cause if empty, else solution if empty, else remark."""
        if not (issue.cause or "").strip():
            return "cause"
        if not (issue.solution or "").strip():
            return "solution"
        return "remark"

    @staticmethod
    def _extract_opencode_text(raw_output):
        """Extract text content from opencode --format json event stream."""
        texts = []
        for line in raw_output.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if event.get("type") == "text":
                    text = event.get("part", {}).get("text", "")
                    if text:
                        texts.append(text)
            except (json.JSONDecodeError, TypeError):
                continue
        return "\n".join(texts)

    def get_running_analysis(self, issue):
        # First clean up any stuck analyses (>10min = dead thread)
        cutoff = timezone.now() - timedelta(minutes=10)
        Analysis.objects.filter(
            issue=issue,
            analysis_type="issue_code_analysis",
            status=Analysis.Status.RUNNING,
            created_at__lt=cutoff,
        ).update(status=Analysis.Status.FAILED, error_message="分析超时，请重试")

        return Analysis.objects.filter(
            issue=issue,
            analysis_type="issue_code_analysis",
            status=Analysis.Status.RUNNING,
        ).first()

    @classmethod
    def cleanup_stale_analyses(cls):
        cutoff = timezone.now() - timedelta(minutes=10)
        Analysis.objects.filter(
            status=Analysis.Status.RUNNING,
            created_at__lt=cutoff,
        ).update(status=Analysis.Status.FAILED, error_message="进程异常终止")
