"""Tests for the Notification admin's publish-to-test/prod detail actions."""
from unittest.mock import patch

import pytest
from django.contrib import admin as django_admin
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory

from apps.notifications.models import Notification
from apps.notifications.services import RemotePublishError
from tests.factories import NotificationFactory, UserFactory


def _admin_request(method="post", path="/admin/", user=None):
    factory = RequestFactory()
    request = getattr(factory, method)(path)
    request.user = user or UserFactory(is_staff=True, is_superuser=True)
    setattr(request, "session", {})
    setattr(request, "_messages", FallbackStorage(request))
    return request


@pytest.fixture
def admin_instance():
    from apps.notifications.admin import NotificationAdmin
    return NotificationAdmin(Notification, django_admin.site)


@pytest.mark.django_db
class TestNotificationAdminPublishActions:
    def test_actions_detail_lists_both_buttons(self, admin_instance):
        assert "publish_to_test" in admin_instance.actions_detail
        assert "publish_to_prod" in admin_instance.actions_detail

    def test_publish_to_test_calls_service_with_test_env(self, admin_instance):
        notif = NotificationFactory()
        request = _admin_request()

        with patch("apps.notifications.admin.publish_notification_to_remote") as mock_pub:
            mock_pub.return_value = {"id": "remote-id", "recipients": 7}
            admin_instance.publish_to_test(request, str(notif.pk))

        mock_pub.assert_called_once()
        called_notif, kwargs = mock_pub.call_args.args[0], mock_pub.call_args.kwargs
        assert called_notif.pk == notif.pk
        assert kwargs == {"env": "test"}

    def test_publish_to_prod_calls_service_with_prod_env(self, admin_instance):
        notif = NotificationFactory()
        request = _admin_request()

        with patch("apps.notifications.admin.publish_notification_to_remote") as mock_pub:
            mock_pub.return_value = {"id": "remote-id", "recipients": 7}
            admin_instance.publish_to_prod(request, str(notif.pk))

        mock_pub.assert_called_once()
        called_notif, kwargs = mock_pub.call_args.args[0], mock_pub.call_args.kwargs
        assert called_notif.pk == notif.pk
        assert kwargs == {"env": "prod"}

    def test_success_shows_success_message(self, admin_instance):
        notif = NotificationFactory()
        request = _admin_request()

        with patch("apps.notifications.admin.publish_notification_to_remote") as mock_pub:
            mock_pub.return_value = {"id": "remote", "recipients": 12}
            admin_instance.publish_to_test(request, str(notif.pk))

        messages = list(request._messages)
        assert len(messages) == 1
        assert messages[0].level_tag == "success"
        assert "12" in messages[0].message  # recipient count surfaced

    def test_improperly_configured_shows_error_message(self, admin_instance):
        notif = NotificationFactory()
        request = _admin_request()

        with patch("apps.notifications.admin.publish_notification_to_remote") as mock_pub:
            mock_pub.side_effect = ImproperlyConfigured("DEVTRAKR_TEST_KEY is not set")
            admin_instance.publish_to_test(request, str(notif.pk))

        messages = list(request._messages)
        assert len(messages) == 1
        assert messages[0].level_tag == "error"
        assert "DEVTRAKR_TEST_KEY" in messages[0].message

    def test_remote_failure_shows_error_message(self, admin_instance):
        notif = NotificationFactory()
        request = _admin_request()

        with patch("apps.notifications.admin.publish_notification_to_remote") as mock_pub:
            mock_pub.side_effect = RemotePublishError("remote returned 401")
            admin_instance.publish_to_prod(request, str(notif.pk))

        messages = list(request._messages)
        assert len(messages) == 1
        assert messages[0].level_tag == "error"
        assert "401" in messages[0].message

    def test_returns_redirect_to_change_view(self, admin_instance):
        from django.http import HttpResponseRedirect

        notif = NotificationFactory()
        request = _admin_request()

        with patch("apps.notifications.admin.publish_notification_to_remote") as mock_pub:
            mock_pub.return_value = {"id": "x", "recipients": 1}
            resp = admin_instance.publish_to_test(request, str(notif.pk))

        assert isinstance(resp, HttpResponseRedirect)
        assert str(notif.pk) in resp.url
