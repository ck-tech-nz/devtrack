import pytest
from tests.factories import LLMConfigFactory, PromptFactory, AnalysisFactory


@pytest.mark.django_db
def test_llmconfig_creation():
    config = LLMConfigFactory(is_default=True)
    assert config.name
    assert config.is_default is True


@pytest.mark.django_db
def test_llmconfig_save_clears_other_defaults():
    from apps.ai.models import LLMConfig

    config1 = LLMConfigFactory(is_default=True)
    config2 = LLMConfigFactory(is_default=True)
    config1.refresh_from_db()
    assert config1.is_default is False
    assert config2.is_default is True


@pytest.mark.django_db
def test_prompt_creation():
    prompt = PromptFactory(slug="team_insights")
    assert prompt.slug == "team_insights"
    assert prompt.is_active is True


@pytest.mark.django_db
def test_analysis_defaults():
    analysis = AnalysisFactory()
    assert analysis.status == "pending"


@pytest.mark.django_db
def test_analysis_str():
    analysis = AnalysisFactory(analysis_type="team_insights", status="done")
    assert "team_insights" in str(analysis)
