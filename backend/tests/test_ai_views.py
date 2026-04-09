from unittest.mock import patch
import pytest
from tests.factories import AnalysisFactory, LLMConfigFactory, PromptFactory


@pytest.mark.django_db
def test_get_insights_returns_cached_result(ai_client):
    AnalysisFactory(
        analysis_type="team_insights", status="done",
        parsed_result={"trend_alerts": []}, data_hash="abc",
    )
    with patch("apps.ai.services.AIAnalysisService._compute_data_hash", return_value="abc"), \
         patch("apps.ai.services.AIAnalysisService._is_stale", return_value=False):
        response = ai_client.get("/api/ai/insights/?type=team_insights")

    assert response.status_code == 200
    assert response.data["status"] == "done"
    assert response.data["result"] == {"trend_alerts": []}


@pytest.mark.django_db
def test_get_insights_returns_202_when_no_result(ai_client):
    """When no cached result exists, dispatch task and return 202."""
    LLMConfigFactory(is_default=True)
    PromptFactory(slug="team_insights")

    with patch("apps.ai.tasks.run_team_insights.delay") as mock_delay:
        response = ai_client.get("/api/ai/insights/?type=team_insights")

    assert response.status_code == 202
    assert response.data["status"] == "pending"
    mock_delay.assert_called_once()


@pytest.mark.django_db
def test_get_insights_503_when_no_config(ai_client):
    """No LLMConfig and no Prompt -> 503."""
    response = ai_client.get("/api/ai/insights/?type=team_insights")
    assert response.status_code == 503


@pytest.mark.django_db
def test_post_refresh_returns_202(ai_client):
    """Refresh dispatches task and returns 202."""
    with patch("apps.ai.tasks.refresh_team_insights.delay") as mock_delay:
        response = ai_client.post(
            "/api/ai/insights/refresh/", {"type": "team_insights"}, format="json"
        )

    assert response.status_code == 202
    assert response.data["status"] == "pending"
    mock_delay.assert_called_once()


@pytest.mark.django_db
def test_insights_requires_authentication(api_client):
    response = api_client.get("/api/ai/insights/?type=team_insights")
    assert response.status_code == 401


@pytest.mark.django_db
def test_sync_github_requires_staff(ai_client):
    response = ai_client.post("/api/ai/sync-github/")
    assert response.status_code == 403
