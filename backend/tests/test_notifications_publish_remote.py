"""Tests for publishing a local notification to a remote DevTrakr server (test/prod)."""
from unittest.mock import patch, MagicMock

import pytest
from django.core.exceptions import ImproperlyConfigured

from tests.factories import NotificationFactory


@pytest.fixture
def remote_settings(settings):
    settings.DEVTRAKR_TEST_URL = "https://test.example/api/external/notifications/create/"
    settings.DEVTRAKR_TEST_KEY = "sk-test-xxx"
    settings.DEVTRAKR_PROD_URL = "https://prod.example/api/external/notifications/create/"
    settings.DEVTRAKR_PROD_KEY = "sk-prod-yyy"
    return settings


@pytest.mark.django_db
class TestPublishNotificationToRemote:
    def _mock_response(self, status_code=201, json_data=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.ok = 200 <= status_code < 300
        resp.json.return_value = json_data or {"id": "remote-uuid", "recipients": 5}
        return resp

    def test_publish_to_test_uses_test_url_and_key(self, remote_settings):
        from apps.notifications.services import publish_notification_to_remote
        notif = NotificationFactory(title="t", content="c", target_type="all")

        with patch("apps.notifications.services.requests.post") as mock_post:
            mock_post.return_value = self._mock_response()
            publish_notification_to_remote(notif, env="test")

        call_args = mock_post.call_args
        assert call_args.args[0] == "https://test.example/api/external/notifications/create/"
        assert call_args.kwargs["headers"]["Authorization"] == "Bearer sk-test-xxx"

    def test_publish_to_prod_uses_prod_url_and_key(self, remote_settings):
        from apps.notifications.services import publish_notification_to_remote
        notif = NotificationFactory(title="t", content="c", target_type="all")

        with patch("apps.notifications.services.requests.post") as mock_post:
            mock_post.return_value = self._mock_response()
            publish_notification_to_remote(notif, env="prod")

        call_args = mock_post.call_args
        assert call_args.args[0] == "https://prod.example/api/external/notifications/create/"
        assert call_args.kwargs["headers"]["Authorization"] == "Bearer sk-prod-yyy"

    def test_publish_to_test_forces_is_draft_true(self, remote_settings):
        from apps.notifications.services import publish_notification_to_remote
        notif = NotificationFactory(title="t", content="c", target_type="all", is_draft=False)

        with patch("apps.notifications.services.requests.post") as mock_post:
            mock_post.return_value = self._mock_response()
            publish_notification_to_remote(notif, env="test")

        payload = mock_post.call_args.kwargs["json"]
        assert payload["is_draft"] is True

    def test_publish_to_prod_forces_is_draft_false(self, remote_settings):
        from apps.notifications.services import publish_notification_to_remote
        notif = NotificationFactory(title="t", content="c", target_type="all", is_draft=True)

        with patch("apps.notifications.services.requests.post") as mock_post:
            mock_post.return_value = self._mock_response()
            publish_notification_to_remote(notif, env="prod")

        payload = mock_post.call_args.kwargs["json"]
        assert payload["is_draft"] is False

    def test_payload_includes_title_content_target(self, remote_settings):
        from apps.notifications.services import publish_notification_to_remote
        notif = NotificationFactory(
            title="标题", content="内容", target_type="all",
        )

        with patch("apps.notifications.services.requests.post") as mock_post:
            mock_post.return_value = self._mock_response()
            publish_notification_to_remote(notif, env="test")

        payload = mock_post.call_args.kwargs["json"]
        assert payload["title"] == "标题"
        assert payload["content"] == "内容"
        assert payload["target_type"] == "all"

    def test_returns_remote_response_data(self, remote_settings):
        from apps.notifications.services import publish_notification_to_remote
        notif = NotificationFactory(target_type="all")

        with patch("apps.notifications.services.requests.post") as mock_post:
            mock_post.return_value = self._mock_response(
                json_data={"id": "abc-123", "recipients": 42},
            )
            result = publish_notification_to_remote(notif, env="prod")

        assert result == {"id": "abc-123", "recipients": 42}

    def test_missing_url_raises_improperly_configured(self, settings):
        settings.DEVTRAKR_TEST_URL = ""
        settings.DEVTRAKR_TEST_KEY = "sk-test"
        from apps.notifications.services import publish_notification_to_remote
        notif = NotificationFactory(target_type="all")

        with pytest.raises(ImproperlyConfigured, match="DEVTRAKR_TEST_URL"):
            publish_notification_to_remote(notif, env="test")

    def test_missing_key_raises_improperly_configured(self, settings):
        settings.DEVTRAKR_PROD_URL = "https://prod.example"
        settings.DEVTRAKR_PROD_KEY = ""
        from apps.notifications.services import publish_notification_to_remote
        notif = NotificationFactory(target_type="all")

        with pytest.raises(ImproperlyConfigured, match="DEVTRAKR_PROD_KEY"):
            publish_notification_to_remote(notif, env="prod")

    def test_invalid_env_raises_value_error(self, remote_settings):
        from apps.notifications.services import publish_notification_to_remote
        notif = NotificationFactory(target_type="all")

        with pytest.raises(ValueError, match="env"):
            publish_notification_to_remote(notif, env="staging")

    def test_non_2xx_response_raises(self, remote_settings):
        from apps.notifications.services import publish_notification_to_remote, RemotePublishError
        notif = NotificationFactory(target_type="all")

        with patch("apps.notifications.services.requests.post") as mock_post:
            mock_post.return_value = self._mock_response(
                status_code=401, json_data={"detail": "认证失败"},
            )
            with pytest.raises(RemotePublishError, match="401"):
                publish_notification_to_remote(notif, env="test")
