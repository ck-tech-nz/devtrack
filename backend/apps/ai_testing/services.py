from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

import apps.tools.storage as tools_storage
from apps.ai.models import LLMConfig
from apps.issues.services import create_issue
from apps.settings.models import SiteSettings
from apps.tools.models import Attachment

from .agent import AITestAgent, AgentDecision
from .browser import (
    BrowserRuntimeUnavailable,
    BrowserToolResult,
    HeadlessBrowserSession,
)
from .models import AITestingModelSettings, BrowserArtifact, TestRun, TestStepRun

logger = logging.getLogger(__name__)

DEFAULT_LOGIN_ENTRY_TARGET = (
    'css=a[href*="/login"], button:has-text("登录"), [role="button"]:has-text("登录"), '
    'button:has-text("Login"), [role="button"]:has-text("Login")'
)
DEFAULT_USERNAME_TARGET = (
    'css=input[name="username"], input[name="account"], input[name="email"], input[name="mobile"], '
    'input[id*="user" i], input[id*="account" i], input[id*="email" i], input[autocomplete="username"], '
    'input[placeholder*="用户名"], input[placeholder*="账号"], input[placeholder*="邮箱"], '
    'input[type="email"], input[type="text"]'
)
DEFAULT_PASSWORD_TARGET = (
    'css=input[type="password"], input[name="password"], input[name="passwd"], input[name="pwd"], '
    'input[id*="pass" i], input[autocomplete="current-password"], input[autocomplete="new-password"], '
    'input[placeholder*="密码"], input[placeholder*="Password"]'
)
DEFAULT_SUBMIT_TARGET = 'css=button[type="submit"], input[type="submit"], button:has-text("登录"), [role="button"]:has-text("登录")'
DEFAULT_LOGIN_PATH = "/login"


@dataclass
class SuggestedIssuePayload:
    project_id: int
    title: str
    description: str
    priority: str
    source: str
    source_meta: dict


def build_failed_run_issue_payload(*, run_id: int, project_id: int, run_name: str, status: str, summary: str) -> SuggestedIssuePayload:
    return SuggestedIssuePayload(
        project_id=project_id,
        title=f"[AI测试失败] {run_name}",
        description=summary,
        priority="P2",
        source="ai_testing",
        source_meta={"test_run_id": run_id, "status": status},
    )


def _pick_default_labels() -> list[str]:
    labels = SiteSettings.get_solo().labels
    if isinstance(labels, dict) and "AI测试" in labels:
        return ["AI测试"]
    if isinstance(labels, list) and "AI测试" in labels:
        return ["AI测试"]
    return []


def _build_run_failure_description(run: TestRun) -> str:
    lines = [
        f"测试执行 ID: {run.id}",
        f"执行名称: {run.name}",
        f"执行状态: {run.status}",
        f"目标地址: {run.target_url or '-'}",
        f"环境: {run.environment.name} ({run.environment.base_url})",
        "",
        "失败原因:",
        run.failure_reason or "未记录",
        "",
        "最终摘要:",
        run.final_summary or "未记录",
    ]
    steps = run.steps.order_by("step_index", "id")[:8]
    if steps:
        lines.extend(["", "关键步骤:"])
        for step in steps:
            lines.append(
                f"{step.step_index}. {step.tool_name} [{step.status}] {step.error_message or ''}".strip()
            )
    return "\n".join(lines)


def create_issue_for_failed_run(*, run: TestRun, actor):
    if run.status not in {TestRun.STATUS_FAILED, TestRun.STATUS_TIMEOUT, TestRun.STATUS_CANCELLED}:
        raise ValueError("仅失败/超时/取消的执行可以创建问题")

    payload = build_failed_run_issue_payload(
        run_id=run.id,
        project_id=run.project_id,
        run_name=run.name,
        status=run.status,
        summary=_build_run_failure_description(run),
    )
    issue = create_issue(
        project=run.project,
        actor=actor,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        source=payload.source,
        source_meta={
            **payload.source_meta,
            "environment_id": run.environment_id,
            "flow_id": run.flow_id,
        },
        labels=_pick_default_labels(),
        reporter="",
    )
    return issue


def _pick_runtime_model_settings(run: TestRun) -> AITestingModelSettings | None:
    if run.environment.model_settings_id:
        return run.environment.model_settings
    return (
        AITestingModelSettings.objects.select_related("llm_config")
        .filter(is_global_default=True)
        .first()
    )


def _pick_llm_config(model_settings: AITestingModelSettings | None) -> LLMConfig | None:
    if model_settings and model_settings.llm_config_id:
        return model_settings.llm_config
    return (
        LLMConfig.objects.filter(is_active=True, is_default=True).first()
        or LLMConfig.objects.filter(is_active=True).first()
    )


def _pick_planner_model(model_settings: AITestingModelSettings | None, llm_config: LLMConfig | None) -> str:
    if model_settings and model_settings.planner_model:
        return model_settings.planner_model
    if llm_config and llm_config.available_models:
        return llm_config.available_models[0]
    return ""


def _build_seed_actions(run: TestRun, target_url: str) -> list[AgentDecision]:
    flow = run.flow
    env = run.environment
    cfg = env.login_config if isinstance(env.login_config, dict) else {}

    actions: list[AgentDecision] = [AgentDecision("open_url", {"url": target_url}, "打开测试入口")]
    if env.login_type == env.LOGIN_USERNAME_PASSWORD and env.login_username and env.has_login_password:
        login_entry_target = cfg.get("login_entry_target") or DEFAULT_LOGIN_ENTRY_TARGET
        login_url = cfg.get("login_url") or DEFAULT_LOGIN_PATH
        username_target = cfg.get("username_target") or DEFAULT_USERNAME_TARGET
        password_target = cfg.get("password_target") or DEFAULT_PASSWORD_TARGET
        submit_target = cfg.get("submit_target") or DEFAULT_SUBMIT_TARGET
        post_login_wait_text = cfg.get("post_login_wait_text") or ""
        if login_entry_target:
            actions.append(
                AgentDecision(
                    "click",
                    {"target": login_entry_target},
                    "尝试打开登录表单",
                    allow_failure=True,
                )
            )
        if login_url:
            actions.append(
                AgentDecision(
                    "open_url",
                    {"url": login_url},
                    "尝试直接进入登录页面",
                    allow_failure=True,
                )
            )
        actions.extend(
            [
                AgentDecision(
                    "fill",
                    {"target": username_target, "value": env.login_username},
                    "填入测试账号",
                    allow_failure=True,
                ),
                AgentDecision(
                    "fill",
                    {"target": password_target, "value": env.get_login_password()},
                    "填入测试密码",
                    allow_failure=True,
                ),
                AgentDecision(
                    "click",
                    {"target": submit_target},
                    "提交登录",
                    allow_failure=True,
                ),
            ]
        )
        if post_login_wait_text:
            actions.append(
                AgentDecision(
                    "wait_for_text",
                    {"text": post_login_wait_text, "timeout_ms": 15000},
                    "等待登录后关键文本",
                    allow_failure=True,
                )
            )

    if flow and flow.target_url and flow.target_url != target_url:
        actions.append(AgentDecision("open_url", {"url": flow.target_url}, "进入流程起始地址"))
    return actions


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            key = str(k).lower()
            if any(token in key for token in ("password", "token", "secret", "cookie", "authorization", "api_key")):
                out[k] = "***"
            else:
                out[k] = _redact_value(v)
        return out
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    return value


def _store_screenshot_artifact(
    *,
    run: TestRun,
    step: TestStepRun,
    file_name: str,
    content: bytes,
    mime_type: str = "image/png",
) -> BrowserArtifact | None:
    try:
        upload = SimpleUploadedFile(file_name, content, content_type=mime_type)
        url, key = tools_storage.upload_image(upload)
        attachment = Attachment.objects.create(
            uploaded_by=run.created_by,
            file_name=file_name,
            file_key=key,
            file_url=url,
            file_size=len(content),
            mime_type=mime_type,
            content_hash=hashlib.sha256(content).hexdigest(),
        )
        return BrowserArtifact.objects.create(
            run=run,
            step=step,
            artifact_type=BrowserArtifact.TYPE_SCREENSHOT,
            attachment=attachment,
            metadata={"file_name": file_name},
        )
    except Exception:
        logger.exception("ai-testing screenshot artifact storage failed for run=%s step=%s", run.id, step.id)
        return None


def _store_text_artifact(*, run: TestRun, artifact_type: str, content: str, metadata: dict[str, Any] | None = None):
    if not content.strip():
        return None
    return BrowserArtifact.objects.create(
        run=run,
        artifact_type=artifact_type,
        content=content[:20000],
        metadata=metadata or {},
    )


def _append_step(
    *,
    run: TestRun,
    step_index: int,
    decision: AgentDecision,
    result: BrowserToolResult,
) -> TestStepRun:
    step = TestStepRun.objects.create(
        run=run,
        step_index=step_index,
        skill_name="generic_harness",
        thought_summary=decision.thought_summary,
        tool_name=decision.tool_name,
        tool_input=_redact_value(decision.tool_input),
        tool_result=_redact_value(result.data),
        page_url=result.page_url or "",
        status=TestStepRun.STATUS_SUCCESS if result.ok else TestStepRun.STATUS_FAILED,
        error_message="" if result.ok else result.message,
    )
    if result.screenshot:
        _store_screenshot_artifact(
            run=run,
            step=step,
            file_name=result.screenshot.file_name,
            content=result.screenshot.content,
            mime_type=result.screenshot.mime_type,
        )
    return step


def _append_runtime_failure_step(run: TestRun, error_message: str):
    last = TestStepRun.objects.filter(run=run).order_by("-step_index", "-id").first()
    step_index = (last.step_index + 1) if last else 1
    TestStepRun.objects.create(
        run=run,
        step_index=step_index,
        skill_name="system",
        thought_summary="执行器异常",
        tool_name="runtime_error",
        tool_input={},
        tool_result={},
        page_url=run.target_url or "",
        status=TestStepRun.STATUS_FAILED,
        error_message=error_message[:2000],
    )


def _store_runtime_logs(run: TestRun, browser: HeadlessBrowserSession):
    _store_text_artifact(
        run=run,
        artifact_type=BrowserArtifact.TYPE_CONSOLE,
        content="\n".join(f"[{item.get('type', '')}] {item.get('text', '')}" for item in browser.console_logs[-80:]),
        metadata={"log_count": len(browser.console_logs)},
    )
    _store_text_artifact(
        run=run,
        artifact_type=BrowserArtifact.TYPE_NETWORK,
        content="\n".join(
            f"{item.get('method', '')} {item.get('url', '')} :: {item.get('failure', '')}"
            for item in browser.network_errors[-80:]
        ),
        metadata={"error_count": len(browser.network_errors)},
    )


def execute_ai_test_run(run: TestRun):
    run = TestRun.objects.select_related("flow", "environment", "project").get(pk=run.pk)
    if run.status != TestRun.STATUS_PENDING:
        return run

    flow = run.flow
    env = run.environment
    model_settings = _pick_runtime_model_settings(run)
    llm_config = _pick_llm_config(model_settings)
    planner_model = _pick_planner_model(model_settings, llm_config)

    max_steps = flow.max_steps if flow else 30
    max_steps = max(1, min(max_steps, model_settings.max_agent_turns if model_settings else max_steps))
    run_timeout_secs = flow.timeout_secs if flow else 300
    tool_timeout_secs = model_settings.tool_call_timeout_secs if model_settings else 60
    temperature = model_settings.temperature if model_settings else 0.1

    target_url = run.target_url or (flow.target_url if flow else "") or env.base_url
    seed_actions = _build_seed_actions(run, target_url)
    login_hint = ""
    if env.login_type == env.LOGIN_USERNAME_PASSWORD and env.login_username:
        login_hint = (
            f"请使用环境账号 {env.login_username}，密码由系统自动注入，不要记录明文。"
            "系统会先执行登录 seed 步骤；只有在页面明确仍停留登录表单时，才重复登录动作。"
        )

    run.status = TestRun.STATUS_RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at", "updated_at"])

    agent = AITestAgent(
        llm_config=llm_config,
        model=planner_model,
        temperature=temperature,
        timeout_secs=tool_timeout_secs,
        seed_actions=seed_actions,
    )

    history: list[dict[str, Any]] = []
    observation: dict[str, Any] = {}
    last_result: BrowserToolResult | None = None
    started_monotonic = time.monotonic()

    try:
        with HeadlessBrowserSession(
            base_url=env.base_url,
            allowed_url_patterns=env.allowed_url_patterns or [],
            allow_write_actions=env.allow_write_actions,
            allow_dangerous_actions=env.allow_dangerous_actions,
            timeout_ms=tool_timeout_secs * 1000,
            headless=True,
        ) as browser:
            for step_index in range(1, max_steps + 1):
                run.refresh_from_db(fields=["status"])
                if run.status == TestRun.STATUS_CANCELLED:
                    run.final_summary = "执行被用户取消"
                    run.failure_reason = "cancelled_by_user"
                    run.finished_at = timezone.now()
                    run.save(update_fields=["final_summary", "failure_reason", "finished_at", "updated_at"])
                    return run

                if time.monotonic() - started_monotonic > run_timeout_secs:
                    timeout_step = TestStepRun.objects.create(
                        run=run,
                        step_index=step_index,
                        skill_name="system",
                        thought_summary="执行超时保护触发",
                        tool_name="timeout_guard",
                        tool_input={"run_timeout_secs": run_timeout_secs},
                        tool_result={},
                        page_url=browser.page.url if browser.page else (run.target_url or ""),
                        status=TestStepRun.STATUS_FAILED,
                        error_message=f"执行超时（>{run_timeout_secs}s）",
                    )
                    shot = browser.execute_tool("take_screenshot", {"reason": "timeout", "step_index": step_index})
                    if shot.screenshot:
                        _store_screenshot_artifact(
                            run=run,
                            step=timeout_step,
                            file_name=shot.screenshot.file_name,
                            content=shot.screenshot.content,
                            mime_type=shot.screenshot.mime_type,
                        )
                    run.status = TestRun.STATUS_TIMEOUT
                    run.failure_reason = f"执行超时（>{run_timeout_secs}s）"
                    run.final_summary = "执行超时，已强制结束"
                    run.finished_at = timezone.now()
                    _store_runtime_logs(run=run, browser=browser)
                    run.save(
                        update_fields=["status", "failure_reason", "final_summary", "finished_at", "updated_at"]
                    )
                    return run

                decision = agent.next_decision(
                    run_name=run.name,
                    target_url=target_url,
                    flow_description=(flow.description if flow else "") or "",
                    success_criteria=(flow.success_criteria if flow else "") or "",
                    login_hint=login_hint,
                    step_index=step_index,
                    max_steps=max_steps,
                    observation=observation,
                    history=history,
                )
                result = browser.execute_tool(decision.tool_name, decision.tool_input)
                _append_step(run=run, step_index=step_index, decision=decision, result=result)
                last_result = result

                history.append(
                    {
                        "step": step_index,
                        "tool": decision.tool_name,
                        "ok": result.ok,
                        "message": result.message,
                        "url": result.page_url,
                    }
                )

                if decision.tool_name == "observe_page":
                    observation = result.data if isinstance(result.data, dict) else {}
                elif decision.tool_name == "take_screenshot":
                    observation = {"screenshot_taken": True, "url": result.page_url}
                elif decision.tool_name.startswith("finish_"):
                    if decision.tool_name == "finish_success" and result.ok:
                        run.status = TestRun.STATUS_SUCCESS
                        run.final_summary = result.message or "执行成功"
                        run.failure_reason = ""
                    else:
                        run.status = TestRun.STATUS_FAILED
                        run.final_summary = "执行失败"
                        run.failure_reason = result.message or "finish_failure"
                    break
                else:
                    observation = {"last_tool": decision.tool_name, "last_message": result.message, "url": result.page_url}

                if not result.ok:
                    shot = browser.execute_tool(
                        "take_screenshot",
                        {"reason": f"failure_step_{step_index}", "step_index": step_index},
                    )
                    failure_step = TestStepRun.objects.filter(run=run, step_index=step_index).first()
                    if failure_step and shot.screenshot:
                        _store_screenshot_artifact(
                            run=run,
                            step=failure_step,
                            file_name=shot.screenshot.file_name,
                            content=shot.screenshot.content,
                            mime_type=shot.screenshot.mime_type,
                        )
                    if decision.allow_failure:
                        observation = {
                            "last_tool": decision.tool_name,
                            "last_message": result.message,
                            "url": result.page_url,
                            "optional_failure": True,
                        }
                        continue
                    run.status = TestRun.STATUS_FAILED
                    run.failure_reason = result.message or "tool_failed"
                    run.final_summary = f"第 {step_index} 步失败：{decision.tool_name}"
                    break

                # Seed actions often include login and may trigger delayed redirects.
                # Refresh observation once right after seed phase so the model does not reason on stale login-page state.
                if step_index == len(seed_actions):
                    try:
                        browser.page.wait_for_load_state("networkidle", timeout=min(5000, tool_timeout_secs * 1000))
                    except Exception:
                        pass
                    refresh = browser.execute_tool("observe_page", {"max_text": 1200, "max_elements": 40})
                    if refresh.ok and isinstance(refresh.data, dict):
                        observation = refresh.data

            if run.status == TestRun.STATUS_RUNNING:
                if last_result and last_result.ok:
                    run.status = TestRun.STATUS_SUCCESS
                    run.final_summary = last_result.message or "执行完成"
                    run.failure_reason = ""
                else:
                    run.status = TestRun.STATUS_FAILED
                    run.failure_reason = (last_result.message if last_result else "") or "未达到成功条件"
                    run.final_summary = "执行结束但未满足成功条件"

            _store_runtime_logs(run=run, browser=browser)

    except BrowserRuntimeUnavailable as exc:
        run.status = TestRun.STATUS_FAILED
        run.failure_reason = str(exc)
        run.final_summary = "浏览器运行时不可用，执行失败"
        if not TestStepRun.objects.filter(run=run).exists():
            _append_runtime_failure_step(run, str(exc))
    except Exception as exc:  # pragma: no cover - runtime safeguard
        logger.exception("ai-testing run failed: run=%s", run.id)
        run.status = TestRun.STATUS_FAILED
        run.failure_reason = str(exc)
        run.final_summary = "执行异常终止"
        if not TestStepRun.objects.filter(run=run).exists():
            _append_runtime_failure_step(run, str(exc))
    finally:
        run.finished_at = timezone.now()
        run.save(
            update_fields=[
                "status",
                "final_summary",
                "failure_reason",
                "finished_at",
                "updated_at",
            ]
        )
    return run


# Backward-compatible alias: old callers still reference execute_minimal_run.
execute_minimal_run = execute_ai_test_run
