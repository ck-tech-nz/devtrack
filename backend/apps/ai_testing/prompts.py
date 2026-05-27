from __future__ import annotations

import json

SYSTEM_PROMPT = (
    "你是软件测试专家代理。"
    "你只能输出 JSON，不允许输出 markdown 或解释性文本。"
    "你必须在受控工具集合中选择一个工具执行下一步。"
    "每一轮严格输出对象: "
    '{"thought":"简短思路","tool":"工具名","input":{"参数":"值"}}。'
    "当满足成功标准时使用 finish_success；当无法继续时使用 finish_failure。"
)


def build_agent_user_prompt(
    *,
    run_name: str,
    target_url: str,
    flow_description: str,
    success_criteria: str,
    login_hint: str,
    step_index: int,
    max_steps: int,
    observation: dict,
    history: list[dict],
) -> str:
    return (
        "任务上下文:\n"
        f"- run_name: {run_name}\n"
        f"- target_url: {target_url}\n"
        f"- flow_description: {flow_description or '-'}\n"
        f"- success_criteria: {success_criteria or '-'}\n"
        f"- login_hint: {login_hint or '-'}\n"
        f"- step: {step_index}/{max_steps}\n\n"
        "当前页面观察:\n"
        f"{json.dumps(observation, ensure_ascii=False)}\n\n"
        "最近执行历史(最多 6 条):\n"
        f"{json.dumps(history[-6:], ensure_ascii=False)}\n\n"
        "可用工具:\n"
        "- open_url {url}\n"
        "- observe_page {max_text,max_elements}\n"
        "- click {target}\n"
        "- fill {target,value}\n"
        "- press {key}\n"
        "- wait_for_text {text,timeout_ms}\n"
        "- assert_text {text,timeout_ms}\n"
        "- take_screenshot {reason}\n"
        "- finish_success {summary}\n"
        "- finish_failure {reason}\n\n"
        "现在只输出 JSON。"
    )
