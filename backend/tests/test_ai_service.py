from unittest.mock import patch, MagicMock
import pytest
from django.utils import timezone
from tests.factories import AnalysisFactory, LLMConfigFactory, PromptFactory


@pytest.mark.django_db
def test_llm_client_calls_openai_with_json_mode():
    from apps.ai.client import LLMClient

    config = LLMConfigFactory(api_key="sk-test", base_url="", supports_json_mode=True)
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"result": "ok"}'

    with patch("apps.ai.client.openai.OpenAI") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.chat.completions.create.return_value = mock_response
        mock_cls.return_value = mock_instance

        result = LLMClient(config).complete("gpt-4o", "sys", "user", 0.3)

    assert result == '{"result": "ok"}'
    kwargs = mock_instance.chat.completions.create.call_args[1]
    assert kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.django_db
def test_llm_client_omits_json_mode_when_not_supported():
    from apps.ai.client import LLMClient

    config = LLMConfigFactory(supports_json_mode=False)
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "hello"

    with patch("apps.ai.client.openai.OpenAI") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.chat.completions.create.return_value = mock_response
        mock_cls.return_value = mock_instance

        LLMClient(config).complete("gpt-4o", "sys", "user", 0.3)

    kwargs = mock_instance.chat.completions.create.call_args[1]
    assert "response_format" not in kwargs


@pytest.mark.django_db
def test_parse_json_response_plain():
    from apps.ai.services import parse_json_response

    assert parse_json_response('{"key": "val"}') == {"key": "val"}


@pytest.mark.django_db
def test_parse_json_response_strips_fences():
    from apps.ai.services import parse_json_response

    raw = '```json\n{"key": "val"}\n```'
    assert parse_json_response(raw) == {"key": "val"}


@pytest.mark.django_db
def test_get_or_run_returns_fresh_cache():
    from apps.ai.services import AIAnalysisService

    fresh = AnalysisFactory(
        analysis_type="team_insights", status="done",
        parsed_result={"cached": True}, data_hash="abc",
    )
    with patch("apps.ai.services.AIAnalysisService._compute_data_hash", return_value="abc"):
        result = AIAnalysisService().get_or_run("team_insights", "page_open")

    assert result.id == fresh.id


@pytest.mark.django_db
def test_get_or_run_reruns_when_stale_by_time():
    from apps.ai.services import AIAnalysisService
    from apps.ai.models import Analysis

    # created_at uses auto_now_add so we must bypass it with update()
    obj = AnalysisFactory(analysis_type="team_insights", status="done", data_hash="abc")
    from datetime import timedelta
    stale_time = timezone.now() - timedelta(hours=2)
    Analysis.objects.filter(pk=obj.pk).update(created_at=stale_time)
    LLMConfigFactory(is_default=True)
    PromptFactory(slug="team_insights")

    with patch("apps.ai.services.AIAnalysisService._compute_data_hash", return_value="abc"), \
         patch("apps.ai.services.LLMClient") as mock_cls:
        mock_cls.return_value.complete.return_value = '{"trend_alerts": []}'
        AIAnalysisService().get_or_run("team_insights", "page_open")

    assert Analysis.objects.filter(status="done").count() == 2


@pytest.mark.django_db
def test_get_or_run_reruns_when_stale_by_hash():
    from apps.ai.services import AIAnalysisService
    from apps.ai.models import Analysis

    # Fresh analysis (created now, not time-stale) but data has changed
    AnalysisFactory(analysis_type="team_insights", status="done", data_hash="old_hash")
    LLMConfigFactory(is_default=True)
    PromptFactory(slug="team_insights")

    # New hash differs from stored hash -> triggers re-run
    with patch("apps.ai.services.AIAnalysisService._compute_data_hash", return_value="new_hash"), \
         patch("apps.ai.services.LLMClient") as mock_cls:
        mock_cls.return_value.complete.return_value = '{"trend_alerts": []}'
        AIAnalysisService().get_or_run("team_insights", "page_open")

    assert Analysis.objects.filter(status="done").count() == 2


@pytest.mark.django_db
def test_get_or_run_raises_when_no_prompt():
    from apps.ai.services import AIAnalysisService, AIConfigurationError

    with pytest.raises(AIConfigurationError, match="No active Prompt"):
        AIAnalysisService().get_or_run("missing_type", "page_open")


@pytest.mark.django_db
def test_run_saves_failed_status_on_error():
    from apps.ai.services import AIAnalysisService
    from apps.ai.models import Analysis

    LLMConfigFactory(is_default=True)
    PromptFactory(slug="team_insights")

    with patch("apps.ai.services.LLMClient") as mock_cls:
        mock_cls.return_value.complete.side_effect = Exception("API error")
        with pytest.raises(Exception, match="API error"):
            AIAnalysisService().get_or_run("team_insights", "page_open")

    failed = Analysis.objects.filter(status="failed").first()
    assert failed is not None
    assert "API error" in failed.error_message
