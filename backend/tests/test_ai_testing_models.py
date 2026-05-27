import pytest

from tests.factories import AITestingModelSettingsFactory, ProjectEnvironmentFactory

pytestmark = pytest.mark.django_db


def test_project_environment_encrypts_password():
    env = ProjectEnvironmentFactory(login_password="secret-123")
    env.refresh_from_db()
    assert env.login_password_encrypted
    assert "secret-123" not in env.login_password_encrypted
    assert env.get_login_password() == "secret-123"
    assert env.has_login_password is True


def test_global_default_switches_previous_default_off():
    first = AITestingModelSettingsFactory(is_global_default=True)
    second = AITestingModelSettingsFactory(is_global_default=True)
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_global_default is False
    assert second.is_global_default is True
