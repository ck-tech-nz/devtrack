import json
from unittest.mock import patch

import pytest
from tests.factories import IssueFactory, AnalysisFactory, UserFactory


@pytest.mark.django_db
class TestIssueAnalysesEndpoint:
    def test_list_analyses_returns_done(self, auth_client):
        issue = IssueFactory()
        user = UserFactory(name="CK")
        AnalysisFactory(
            analysis_type="issue_code_analysis",
            issue=issue,
            status="done",
            triggered_by="manual",
            triggered_by_user=user,
            parsed_result={"target_field": "cause", "content": "根因在 models.py"},
        )
        resp = auth_client.get(f"/api/issues/{issue.pk}/analyses/")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        item = resp.data[0]
        assert item["status"] == "done"
        assert item["results"] == {"cause": "根因在 models.py"}
        assert item["triggered_by_user"] == "CK"
        assert item["error_message"] is None

    def test_list_analyses_failed_has_error(self, auth_client):
        issue = IssueFactory()
        AnalysisFactory(
            analysis_type="issue_code_analysis",
            issue=issue,
            status="failed",
            error_message="分析超时",
        )
        resp = auth_client.get(f"/api/issues/{issue.pk}/analyses/")
        assert resp.status_code == 200
        assert resp.data[0]["results"] is None
        assert resp.data[0]["error_message"] == "分析超时"

    def test_list_analyses_running_has_no_results(self, auth_client):
        issue = IssueFactory()
        AnalysisFactory(
            analysis_type="issue_code_analysis",
            issue=issue,
            status="running",
        )
        resp = auth_client.get(f"/api/issues/{issue.pk}/analyses/")
        assert resp.status_code == 200
        assert resp.data[0]["results"] is None
        assert resp.data[0]["error_message"] is None

    def test_list_analyses_excludes_other_types(self, auth_client):
        issue = IssueFactory()
        AnalysisFactory(analysis_type="team_insights", issue=issue, status="done")
        AnalysisFactory(analysis_type="issue_code_analysis", issue=issue, status="done",
                        parsed_result={"target_field": "cause", "content": "test"})
        resp = auth_client.get(f"/api/issues/{issue.pk}/analyses/")
        assert len(resp.data) == 1

    def test_list_analyses_ordered_newest_first(self, auth_client):
        issue = IssueFactory()
        a1 = AnalysisFactory(analysis_type="issue_code_analysis", issue=issue, status="done",
                             parsed_result={"target_field": "cause", "content": "old"})
        a2 = AnalysisFactory(analysis_type="issue_code_analysis", issue=issue, status="done",
                             parsed_result={"target_field": "cause", "content": "new"})
        resp = auth_client.get(f"/api/issues/{issue.pk}/analyses/")
        assert resp.data[0]["id"] == a2.id
        assert resp.data[1]["id"] == a1.id

    def test_list_analyses_requires_auth(self, api_client):
        issue = IssueFactory()
        resp = api_client.get(f"/api/issues/{issue.pk}/analyses/")
        assert resp.status_code == 401


@pytest.mark.django_db
class TestIssueAnalysisServiceNoAppend:
    @pytest.fixture(autouse=True)
    def setup(self, db, settings):
        from tests.factories import RepoFactory, PromptFactory, LLMConfigFactory
        settings.REPO_CLONE_DIR = "/tmp/test_repos"
        LLMConfigFactory(is_default=True)
        PromptFactory(
            slug="issue_code_analysis",
            system_prompt="你是代码分析专家",
            user_prompt_template="分析问题: {title}\n描述: {description}",
        )
        self.repo = RepoFactory(clone_status="cloned", full_name="org/test-repo")

    @patch("apps.ai.services.OpenCodeRunner")
    def test_analysis_does_not_modify_issue_fields(self, MockRunner):
        from apps.ai.services import IssueAnalysisService

        issue = IssueFactory(repo=self.repo, cause="用户写的原因", solution="", remark="")
        mock_instance = MockRunner.return_value
        inner = json.dumps({"target_field": "cause", "content": "AI分析结果"})
        mock_instance.run.return_value = json.dumps({
            "type": "text",
            "part": {"text": inner},
        })

        svc = IssueAnalysisService()
        analysis = svc.analyze(issue, triggered_by="manual")

        issue.refresh_from_db()
        assert issue.cause == "用户写的原因"  # unchanged
        assert analysis.status == "done"
        assert analysis.parsed_result["target_field"] == "cause"
