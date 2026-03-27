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

    def test_generate_config(self):
        config = self.runner.generate_config("deepseek-chat")
        assert "provider" in config
        provider = list(config["provider"].values())[0]
        assert provider["options"]["apiKey"] == "sk-test123"
        assert provider["options"]["baseURL"] == "https://api.deepseek.com/v1"
        assert "model" in config

    def test_generate_config_model_in_provider(self):
        config = self.runner.generate_config("deepseek-chat")
        provider = list(config["provider"].values())[0]
        assert "deepseek-chat" in provider["models"]

    @patch("apps.ai.opencode.os.path.exists", return_value=True)
    @patch("apps.ai.opencode.os.unlink")
    @patch("builtins.open", new_callable=mock_open)
    @patch("apps.ai.opencode.subprocess.run")
    def test_run_success(self, mock_run, mock_file, mock_unlink, mock_exists):
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

    @patch("apps.ai.opencode.os.path.exists", return_value=False)
    @patch("builtins.open", new_callable=mock_open)
    @patch("apps.ai.opencode.subprocess.run")
    def test_run_cleans_up_config(self, mock_run, mock_file, mock_exists):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        self.runner.run(repo_path="/tmp/test_repo", prompt="test", model="m")
        # Config file cleanup attempted (os.path.exists returned False so unlink not called)

    @patch("builtins.open", new_callable=mock_open)
    @patch("apps.ai.opencode.subprocess.run")
    def test_run_timeout(self, mock_run, mock_file):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="opencode", timeout=120)
        with pytest.raises(subprocess.TimeoutExpired):
            self.runner.run(repo_path="/tmp/test_repo", prompt="test", model="m")

    def test_check_health_missing_binary(self):
        with patch("apps.ai.opencode.shutil.which", return_value=None):
            assert self.runner.check_health() is False

    def test_check_health_present(self):
        with patch("apps.ai.opencode.shutil.which", return_value="/usr/local/bin/opencode"):
            assert self.runner.check_health() is True
