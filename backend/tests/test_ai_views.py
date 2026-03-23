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
def test_get_insights_503_when_no_config(ai_client):
    response = ai_client.get("/api/ai/insights/?type=team_insights")
    assert response.status_code == 503


@pytest.mark.django_db
def test_get_insights_runs_llm_when_no_cache(ai_client):
    LLMConfigFactory(is_default=True)
    PromptFactory(slug="team_insights")

    with patch("apps.ai.services.LLMClient") as mock_cls:
        mock_cls.return_value.complete.return_value = '{"trend_alerts": []}'
        response = ai_client.get("/api/ai/insights/?type=team_insights")

    assert response.status_code == 200
    assert response.data["status"] == "done"


@pytest.mark.django_db
def test_post_refresh_forces_new_analysis(ai_client):
    LLMConfigFactory(is_default=True)
    PromptFactory(slug="team_insights")

    with patch("apps.ai.services.LLMClient") as mock_cls:
        mock_cls.return_value.complete.return_value = '{"recommendations": []}'
        response = ai_client.post(
            "/api/ai/insights/refresh/", {"type": "team_insights"}, format="json"
        )

    assert response.status_code == 200
    assert response.data["status"] == "done"


@pytest.mark.django_db
def test_insights_requires_authentication(api_client):
    response = api_client.get("/api/ai/insights/?type=team_insights")
    assert response.status_code == 401


@pytest.mark.django_db
def test_sync_github_requires_staff(ai_client):
    response = ai_client.post("/api/ai/sync-github/")
    assert response.status_code == 403
