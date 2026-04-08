import json
import subprocess
import pytest
from unittest.mock import patch, MagicMock, mock_open
from apps.ai.opencode import OpenCodeRunner
from tests.factories import LLMConfigFactory, PromptFactory


class TestOpenCodeRunner:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.config = LLMConfigFactory(
            api_key="sk-test123",
            base_url="https://api.deepseek.com/v1",
        )
        self.prompt = PromptFactory(llm_model="deepseek-chat")
        self.runner = OpenCodeRunner(self.config)

    def test_get_model_id(self):
        model_id = self.runner._get_model_id("deepseek-chat")
        assert "deepseek-chat" in model_id

    def test_get_env_sets_api_key(self):
        self.config.name = "deepseek"
        self.config.save()
        runner = OpenCodeRunner(self.config)
        env = runner._get_env()
        assert "DEEPSEEK_API_KEY" in env
        assert env["DEEPSEEK_API_KEY"] == "sk-test123"

    @patch("apps.ai.opencode._opencode_bin", return_value="/usr/local/bin/opencode")
    @patch("apps.ai.opencode.subprocess.run")
    def test_run_success(self, mock_run, mock_bin):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"target_field": "cause", "content": "分析结果"}',
            stderr="",
        )
        result = self.runner.run(
            repo_path="/tmp/test_repo",
            prompt="分析这个问题",
            model="deepseek-chat",
        )
        assert "分析结果" in result
        mock_run.assert_called_once()

    @patch("apps.ai.opencode._opencode_bin", return_value="/usr/local/bin/opencode")
    @patch("apps.ai.opencode.subprocess.run")
    def test_run_invokes_subprocess(self, mock_run, mock_bin):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        self.runner.run(repo_path="/tmp/test_repo", prompt="test", model="m")
        mock_run.assert_called_once()

    @patch("apps.ai.opencode._opencode_bin", return_value="/usr/local/bin/opencode")
    @patch("apps.ai.opencode.subprocess.run")
    def test_run_timeout(self, mock_run, mock_bin):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="opencode", timeout=120)
        with pytest.raises(subprocess.TimeoutExpired):
            self.runner.run(repo_path="/tmp/test_repo", prompt="test", model="m")

    def test_check_health_missing_binary(self):
        with patch("apps.ai.opencode.shutil.which", return_value=None):
            assert self.runner.check_health() is False

    def test_check_health_present(self):
        with patch("apps.ai.opencode.shutil.which", return_value="/usr/local/bin/opencode"):
            assert self.runner.check_health() is True
