import pytest

from apps.ai_testing.browser import BrowserRuntimeUnavailable, BrowserToolResult, ScreenshotPayload
from apps.ai_testing.models import ProjectEnvironment, TestRun as AITestRunModel
from apps.ai_testing.services import execute_ai_test_run
from tests.factories import AITestFlowFactory, AITestRunFactory, ProjectEnvironmentFactory

pytestmark = pytest.mark.django_db


def test_execute_ai_run_fails_when_browser_runtime_unavailable(monkeypatch):
    run = AITestRunFactory(status=AITestRunModel.STATUS_PENDING)

    class BrokenBrowser:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            raise BrowserRuntimeUnavailable("playwright unavailable in runtime")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("apps.ai_testing.services.HeadlessBrowserSession", BrokenBrowser)

    execute_ai_test_run(run)
    run.refresh_from_db()
    assert run.status == AITestRunModel.STATUS_FAILED
    assert "playwright unavailable" in run.failure_reason
    assert run.finished_at is not None
    assert run.steps.count() == 1
    assert run.steps.first().tool_name == "runtime_error"


def test_execute_ai_run_success_with_fake_browser(monkeypatch):
    env = ProjectEnvironmentFactory(
        login_type=ProjectEnvironment.LOGIN_NONE,
        login_username="",
    )
    flow = AITestFlowFactory(project=env.project, environment=env, success_criteria="")
    run = AITestRunFactory(
        status=AITestRunModel.STATUS_PENDING,
        flow=flow,
        project=flow.project,
        environment=flow.environment,
    )

    class FakeBrowser:
        def __init__(self, *args, **kwargs):
            self.console_logs = []
            self.network_errors = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute_tool(self, tool_name, tool_input):
            if tool_name == "open_url":
                return BrowserToolResult(
                    ok=True,
                    message="opened",
                    data={"status_code": 200},
                    page_url="https://example.com",
                )
            if tool_name == "observe_page":
                return BrowserToolResult(
                    ok=True,
                    message="observed",
                    data={"title": "Demo", "visible_text": "ok"},
                    page_url="https://example.com",
                )
            if tool_name == "finish_success":
                return BrowserToolResult(
                    ok=True,
                    message="done",
                    data={"finished": "success"},
                    page_url="https://example.com",
                )
            return BrowserToolResult(
                ok=True,
                message=f"{tool_name}:ok",
                data={},
                page_url="https://example.com",
            )

    monkeypatch.setattr("apps.ai_testing.services.HeadlessBrowserSession", FakeBrowser)
    execute_ai_test_run(run)
    run.refresh_from_db()
    assert run.status == AITestRunModel.STATUS_SUCCESS
    assert run.steps.count() >= 2


def test_execute_ai_run_does_not_abort_on_optional_login_seed_failures(monkeypatch):
    env = ProjectEnvironmentFactory(
        login_type=ProjectEnvironment.LOGIN_USERNAME_PASSWORD,
        login_username="tester",
        login_password="pass123456",
    )
    flow = AITestFlowFactory(project=env.project, environment=env, success_criteria="")
    run = AITestRunFactory(
        status=AITestRunModel.STATUS_PENDING,
        flow=flow,
        project=flow.project,
        environment=flow.environment,
    )

    class FakeBrowser:
        def __init__(self, *args, **kwargs):
            self.console_logs = []
            self.network_errors = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute_tool(self, tool_name, tool_input):
            if tool_name == "open_url":
                return BrowserToolResult(ok=True, message="opened", data={}, page_url="https://example.com")
            if tool_name in {"click", "fill"}:
                return BrowserToolResult(ok=False, message=f"{tool_name}: target not found", data={}, page_url="https://example.com")
            if tool_name == "take_screenshot":
                return BrowserToolResult(ok=True, message="shot", data={}, page_url="https://example.com")
            if tool_name == "finish_success":
                return BrowserToolResult(ok=True, message="done", data={}, page_url="https://example.com")
            return BrowserToolResult(ok=True, message=f"{tool_name}:ok", data={}, page_url="https://example.com")

    monkeypatch.setattr("apps.ai_testing.services.HeadlessBrowserSession", FakeBrowser)
    execute_ai_test_run(run)
    run.refresh_from_db()

    assert run.status == AITestRunModel.STATUS_SUCCESS
    assert run.steps.filter(status="failed").count() >= 1


def test_execute_ai_run_timeout_persists_timeout_step_and_runtime_artifacts(monkeypatch):
    env = ProjectEnvironmentFactory(
        login_type=ProjectEnvironment.LOGIN_NONE,
        login_username="",
    )
    flow = AITestFlowFactory(project=env.project, environment=env, success_criteria="", timeout_secs=0)
    run = AITestRunFactory(
        status=AITestRunModel.STATUS_PENDING,
        flow=flow,
        project=flow.project,
        environment=flow.environment,
    )

    class FakeBrowser:
        def __init__(self, *args, **kwargs):
            self.console_logs = [{"type": "log", "text": "hello-timeout"}]
            self.network_errors = [{"method": "GET", "url": "https://example.com/x", "failure": "net::ERR_FAILED"}]
            self.page = type("Page", (), {"url": "https://example.com"})()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute_tool(self, tool_name, tool_input):
            if tool_name == "take_screenshot":
                return BrowserToolResult(
                    ok=True,
                    message="shot",
                    page_url="https://example.com",
                    screenshot=ScreenshotPayload(
                        file_name="timeout.png",
                        content=b"png",
                        mime_type="image/png",
                    ),
                )
            return BrowserToolResult(
                ok=True,
                message=f"{tool_name}:ok",
                data={},
                page_url="https://example.com",
            )

    monkeypatch.setattr("apps.ai_testing.services.HeadlessBrowserSession", FakeBrowser)
    execute_ai_test_run(run)
    run.refresh_from_db()

    assert run.status == AITestRunModel.STATUS_TIMEOUT
    timeout_step = run.steps.order_by("-step_index").first()
    assert timeout_step is not None
    assert timeout_step.tool_name == "timeout_guard"
    artifact_types = sorted(run.artifacts.values_list("artifact_type", flat=True))
    assert "console_log" in artifact_types
    assert "network_log" in artifact_types
