import pytest
from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from tests.factories import UptimeMonitorFactory, UptimeCheckFactory
from apps.uptime.services import decide_transition, TransitionAction
from apps.uptime.services import fire_failure
from apps.issues.models import Issue
from apps.notifications.models import Notification, NotificationRecipient
from apps.projects.models import ProjectMember
from tests.factories import ProjectFactory, UserFactory

pytestmark = pytest.mark.django_db


class TestDecideTransition:
    def test_up_to_up_no_action(self):
        monitor = UptimeMonitorFactory(last_status="up", consecutive_failures=0)
        action = decide_transition(monitor, is_up=True)
        assert action == TransitionAction.NONE

    def test_unknown_to_up_no_action(self):
        monitor = UptimeMonitorFactory(last_status="unknown", consecutive_failures=0)
        action = decide_transition(monitor, is_up=True)
        assert action == TransitionAction.NONE

    def test_up_to_down_first_failure_no_action(self):
        monitor = UptimeMonitorFactory(last_status="up", consecutive_failures=0)
        action = decide_transition(monitor, is_up=False)
        assert action == TransitionAction.NONE

    def test_up_to_down_second_failure_no_action(self):
        monitor = UptimeMonitorFactory(last_status="up", consecutive_failures=1)
        action = decide_transition(monitor, is_up=False)
        assert action == TransitionAction.NONE

    def test_up_to_down_third_failure_fires_failure(self):
        monitor = UptimeMonitorFactory(last_status="up", consecutive_failures=2)
        action = decide_transition(monitor, is_up=False)
        assert action == TransitionAction.FIRE_FAILURE

    def test_down_to_down_no_action(self):
        monitor = UptimeMonitorFactory(last_status="down", consecutive_failures=10)
        action = decide_transition(monitor, is_up=False)
        assert action == TransitionAction.NONE

    def test_down_to_up_fires_recovery(self):
        monitor = UptimeMonitorFactory(last_status="down", consecutive_failures=5)
        action = decide_transition(monitor, is_up=True)
        assert action == TransitionAction.FIRE_RECOVERY


class TestFireFailure:
    def _setup(self):
        bot = UserFactory(username="bot")
        project = ProjectFactory()
        member = UserFactory()
        ProjectMember.objects.create(project=project, user=member, role="开发者")
        monitor = UptimeMonitorFactory(
            project=project, name="api-prod",
            url="https://api.example.com/health",
            last_status="up", consecutive_failures=2,
        )
        return bot, project, member, monitor

    def test_creates_issue_in_project(self, site_settings):
        bot, project, member, monitor = self._setup()
        fire_failure(monitor, latest_error="timeout")
        issue = Issue.objects.get(project=project)
        assert "api-prod" in issue.title
        assert "不可达" in issue.title
        assert issue.priority == "P1"
        assert issue.status == "待处理"
        assert issue.created_by == bot
        assert "timeout" in issue.description

    def test_sets_active_incident_issue(self, site_settings):
        bot, project, member, monitor = self._setup()
        fire_failure(monitor, latest_error="timeout")
        monitor.refresh_from_db()
        assert monitor.active_incident_issue is not None
        assert monitor.last_status == "down"
        assert monitor.outage_started_at is not None

    def test_sends_notifications_to_project_members(self, site_settings):
        bot, project, member, monitor = self._setup()
        fire_failure(monitor, latest_error="timeout")
        notification = Notification.objects.get()
        assert "api-prod" in notification.title
        recipients = list(notification.recipients.values_list("user_id", flat=True))
        assert member.id in recipients

    def test_no_bot_user_raises(self, site_settings):
        project = ProjectFactory()
        monitor = UptimeMonitorFactory(
            project=project, last_status="up", consecutive_failures=2,
        )
        with pytest.raises(Exception):
            fire_failure(monitor, latest_error="timeout")
