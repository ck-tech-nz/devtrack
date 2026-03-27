import json
import pytest
from unittest.mock import patch
from apps.ai.services import IssueAnalysisService
from apps.ai.models import Analysis
from tests.factories import (
    IssueFactory, RepoFactory, PromptFactory, LLMConfigFactory, AnalysisFactory,
)


@pytest.mark.django_db
class TestIssueAnalysisService:
    @pytest.fixture(autouse=True)
    def setup(self, db, settings):
        settings.REPO_CLONE_DIR = "/tmp/test_repos"
        self.config = LLMConfigFactory(is_default=True)
        self.prompt = PromptFactory(
            slug="issue_code_analysis",
            system_prompt="你是代码分析专家",
            user_prompt_template="分析问题: {title}\n描述: {description}",
        )
        self.repo = RepoFactory(clone_status="cloned", full_name="org/test-repo")
        self.issue = IssueFactory(repo=self.repo)
        self.svc = IssueAnalysisService()

    @patch("apps.ai.services.OpenCodeRunner")
    def test_analyze_stores_result_in_parsed_result(self, MockRunner):
        mock_instance = MockRunner.return_value
        inner = json.dumps({"target_field": "cause", "content": "根因是空指针"})
        mock_instance.run.return_value = json.dumps({
            "type": "text",
            "part": {"text": inner},
        })

        analysis = self.svc.analyze(self.issue, triggered_by="manual")
        assert analysis.status == "done"
        assert analysis.parsed_result["target_field"] == "cause"
        assert analysis.parsed_result["content"] == "根因是空指针"
        self.issue.refresh_from_db()
        assert "根因是空指针" not in (self.issue.cause or "")

    @patch("apps.ai.services.OpenCodeRunner")
    def test_analyze_invalid_field_falls_back_to_remark(self, MockRunner):
        mock_instance = MockRunner.return_value
        inner = json.dumps({"target_field": "status", "content": "恶意内容"})
        mock_instance.run.return_value = json.dumps({
            "type": "text",
            "part": {"text": inner},
        })

        analysis = self.svc.analyze(self.issue, triggered_by="manual")
        assert analysis.status == "done"
        assert analysis.parsed_result["target_field"] == "remark"

    def test_analyze_requires_cloned_repo(self):
        self.repo.clone_status = "not_cloned"
        self.repo.save()
        with pytest.raises(ValueError, match="请先同步代码"):
            self.svc.analyze(self.issue, triggered_by="manual")

    def test_analyze_requires_repo(self):
        self.issue.repo = None
        self.issue.save()
        with pytest.raises(ValueError, match="请先关联仓库"):
            self.svc.analyze(self.issue, triggered_by="manual")

    def test_no_duplicate_running_analysis(self):
        AnalysisFactory(
            issue=self.issue,
            analysis_type="issue_code_analysis",
            status="running",
        )
        existing = self.svc.get_running_analysis(self.issue)
        assert existing is not None

    def test_cleanup_stale_analyses(self):
        from django.utils import timezone
        from datetime import timedelta
        stale = AnalysisFactory(
            status="running",
            analysis_type="issue_code_analysis",
        )
        Analysis.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - timedelta(minutes=15)
        )
        IssueAnalysisService.cleanup_stale_analyses()
        stale.refresh_from_db()
        assert stale.status == "failed"
        assert "进程异常终止" in stale.error_message


@pytest.mark.django_db
class TestIssueAIAnalyzeView:
    def test_trigger_returns_202(self, auth_client):
        repo = RepoFactory(full_name="org/test-repo", clone_status="cloned")
        issue = IssueFactory(repo=repo)
        with patch("apps.issues.views.IssueAnalysisService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_running_analysis.return_value = None
            mock_svc.analyze_async.return_value = AnalysisFactory(
                issue=issue, status="running"
            )
            resp = auth_client.post(f"/api/issues/{issue.pk}/ai-analyze/")
            assert resp.status_code == 202
            assert "analysis_id" in resp.data

    def test_no_repo_returns_400(self, auth_client):
        issue = IssueFactory(repo=None)
        resp = auth_client.post(f"/api/issues/{issue.pk}/ai-analyze/")
        assert resp.status_code == 400
        assert "关联仓库" in resp.data["detail"]

    def test_not_cloned_returns_400(self, auth_client):
        repo = RepoFactory(full_name="org/test-repo", clone_status="not_cloned")
        issue = IssueFactory(repo=repo)
        resp = auth_client.post(f"/api/issues/{issue.pk}/ai-analyze/")
        assert resp.status_code == 400
        assert "同步代码" in resp.data["detail"]

    def test_already_running_returns_409(self, auth_client):
        repo = RepoFactory(full_name="org/test-repo", clone_status="cloned")
        issue = IssueFactory(repo=repo)
        with patch("apps.issues.views.IssueAnalysisService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_running_analysis.return_value = AnalysisFactory(
                issue=issue, status="running"
            )
            resp = auth_client.post(f"/api/issues/{issue.pk}/ai-analyze/")
            assert resp.status_code == 409

    def test_not_found_returns_404(self, auth_client):
        resp = auth_client.post("/api/issues/99999/ai-analyze/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestAnalysisStatusView:
    def test_returns_status(self, auth_client):
        analysis = AnalysisFactory(status="done")
        resp = auth_client.get(f"/api/ai/analysis/{analysis.pk}/status/")
        assert resp.status_code == 200
        assert resp.data["status"] == "done"

    def test_not_found(self, auth_client):
        resp = auth_client.get("/api/ai/analysis/99999/status/")
        assert resp.status_code == 404
