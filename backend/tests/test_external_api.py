import pytest
from rest_framework.test import APIClient, APIRequestFactory
from tests.factories import ExternalAPIKeyFactory, IssueFactory


@pytest.mark.django_db
class TestExternalAPIKeyModel:
    def test_create_api_key(self):
        api_key = ExternalAPIKeyFactory()
        assert api_key.pk is not None
        assert len(api_key.key) == 64
        assert api_key.is_active is True
        assert api_key.project is not None
        assert api_key.default_assignee is not None

    def test_key_auto_generated_when_blank(self):
        api_key = ExternalAPIKeyFactory(key="")
        assert len(api_key.key) == 64

    def test_str_representation(self):
        api_key = ExternalAPIKeyFactory(name="Test Platform")
        assert str(api_key) == "Test Platform"


@pytest.mark.django_db
class TestIssueSourceFields:
    def test_issue_source_fields_default_null(self):
        issue = IssueFactory()
        assert issue.source is None
        assert issue.source_meta is None

    def test_issue_with_source_meta(self):
        meta = {
            "feedback_id": "FB001",
            "reporter": {"tenant_name": "Test Corp", "user_name": "张三"},
        }
        issue = IssueFactory(source="agent_platform", source_meta=meta)
        issue.refresh_from_db()
        assert issue.source == "agent_platform"
        assert issue.source_meta["feedback_id"] == "FB001"
        assert issue.source_meta["reporter"]["user_name"] == "张三"


@pytest.fixture
def api_key_obj():
    return ExternalAPIKeyFactory()


@pytest.fixture
def external_client(api_key_obj):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {api_key_obj.key}")
    return client


@pytest.mark.django_db
class TestAPIKeyAuthentication:
    def test_valid_key_authenticates(self, api_key_obj):
        from apps.external.authentication import APIKeyAuthentication

        factory = APIRequestFactory()
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {api_key_obj.key}")
        auth = APIKeyAuthentication()
        user, auth_info = auth.authenticate(request)
        assert user == api_key_obj.default_assignee
        assert request.api_key == api_key_obj

    def test_invalid_key_returns_none(self):
        from apps.external.authentication import APIKeyAuthentication

        factory = APIRequestFactory()
        request = factory.get("/", HTTP_AUTHORIZATION="Bearer invalid_key_here")
        auth = APIKeyAuthentication()
        result = auth.authenticate(request)
        assert result is None

    def test_inactive_key_returns_none(self):
        from apps.external.authentication import APIKeyAuthentication

        inactive_key = ExternalAPIKeyFactory(is_active=False)
        factory = APIRequestFactory()
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {inactive_key.key}")
        auth = APIKeyAuthentication()
        result = auth.authenticate(request)
        assert result is None

    def test_missing_header_returns_none(self):
        from apps.external.authentication import APIKeyAuthentication

        factory = APIRequestFactory()
        request = factory.get("/")
        auth = APIKeyAuthentication()
        result = auth.authenticate(request)
        assert result is None
