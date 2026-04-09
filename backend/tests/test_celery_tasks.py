from unittest.mock import patch, MagicMock
import pytest
from tests.factories import LLMConfigFactory, PromptFactory, AnalysisFactory, UserFactory, RepoFactory


@pytest.mark.django_db
class TestRunTeamInsights:
    def test_calls_get_or_run(self):
        LLMConfigFactory(is_default=True)
        PromptFactory(slug="team_insights")

        with patch("apps.ai.services.LLMClient") as mock_cls:
            mock_cls.return_value.complete.return_value = '{"trend_alerts": []}'
            from apps.ai.tasks import run_team_insights
            run_team_insights()

        from apps.ai.models import Analysis
        assert Analysis.objects.filter(
            analysis_type="team_insights", status="done"
        ).exists()

    def test_skips_when_fresh_result_exists(self):
        AnalysisFactory(
            analysis_type="team_insights", status="done",
            parsed_result={"trend_alerts": []}, data_hash="abc",
        )
        with patch("apps.ai.services.AIAnalysisService._compute_data_hash", return_value="abc"), \
             patch("apps.ai.services.AIAnalysisService._run") as mock_run:
            from apps.ai.tasks import run_team_insights
            run_team_insights()
        mock_run.assert_not_called()


@pytest.mark.django_db
class TestRefreshTeamInsights:
    def test_forces_new_analysis_with_user(self):
        LLMConfigFactory(is_default=True)
        PromptFactory(slug="team_insights")
        user = UserFactory()

        with patch("apps.ai.services.LLMClient") as mock_cls:
            mock_cls.return_value.complete.return_value = '{"recommendations": []}'
            from apps.ai.tasks import refresh_team_insights
            refresh_team_insights(user_id=user.id)

        from apps.ai.models import Analysis
        analysis = Analysis.objects.filter(
            analysis_type="team_insights", status="done"
        ).latest("created_at")
        assert analysis.triggered_by == "manual"
        assert analysis.triggered_by_user == user


@pytest.mark.django_db
class TestPullAllRepos:
    def test_pulls_cloned_repos_only(self):
        cloned = RepoFactory(clone_status="cloned")
        not_cloned = RepoFactory(clone_status="not_cloned")

        with patch("apps.repos.tasks.RepoCloneService") as mock_cls:
            from apps.repos.tasks import pull_all_repos
            pull_all_repos()

        mock_cls.return_value.clone_or_pull.assert_called_once()
        call_args = mock_cls.return_value.clone_or_pull.call_args
        assert call_args[0][0].id == cloned.id

    def test_continues_on_error(self):
        RepoFactory(clone_status="cloned")
        RepoFactory(clone_status="cloned")

        with patch("apps.repos.tasks.RepoCloneService") as mock_cls:
            mock_cls.return_value.clone_or_pull.side_effect = [Exception("fail"), None]
            from apps.repos.tasks import pull_all_repos
            pull_all_repos()

        assert mock_cls.return_value.clone_or_pull.call_count == 2


@pytest.mark.django_db
class TestSyncAllRepos:
    def test_syncs_repos_with_token(self):
        with_token = RepoFactory(github_token="ghp_test123")
        without_token = RepoFactory(github_token="")

        with patch("apps.repos.tasks.GitHubSyncService") as mock_cls:
            from apps.repos.tasks import sync_all_repos
            sync_all_repos()

        mock_cls.return_value.sync_repo.assert_called_once()
        call_args = mock_cls.return_value.sync_repo.call_args
        assert call_args[0][0].id == with_token.id

    def test_continues_on_error(self):
        RepoFactory(github_token="ghp_1")
        RepoFactory(github_token="ghp_2")

        with patch("apps.repos.tasks.GitHubSyncService") as mock_cls:
            mock_cls.return_value.sync_repo.side_effect = [Exception("fail"), None]
            from apps.repos.tasks import sync_all_repos
            sync_all_repos()

        assert mock_cls.return_value.sync_repo.call_count == 2
