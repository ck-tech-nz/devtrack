from apps.ai_testing.agent import AITestAgent


class _DummyClient:
    def __init__(self, output: str):
        self.output = output

    def complete(self, **kwargs):
        return self.output


def test_agent_returns_finish_failure_on_invalid_planner_output():
    agent = AITestAgent(
        llm_config=None,
        model="dummy",
        temperature=0.1,
        timeout_secs=10,
    )
    agent._client = _DummyClient("not-json")

    decision = agent.next_decision(
        run_name="run",
        target_url="https://example.com",
        flow_description="",
        success_criteria="",
        login_hint="",
        step_index=4,
        max_steps=30,
        observation={},
        history=[],
    )

    assert decision.tool_name == "finish_failure"
    assert "planner_output_invalid" in decision.tool_input.get("reason", "")
