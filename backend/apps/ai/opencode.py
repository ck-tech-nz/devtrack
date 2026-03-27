import os
import shutil
import subprocess


class OpenCodeRunner:
    def __init__(self, llm_config):
        self.llm_config = llm_config

    def check_health(self) -> bool:
        return shutil.which("opencode") is not None

    def _get_model_id(self, model: str) -> str:
        """Map LLMConfig name to opencode provider/model format."""
        provider_id = self.llm_config.name.lower().replace(" ", "_")
        return f"{provider_id}/{model}"

    def _get_env(self) -> dict:
        """Build env with API key for the configured provider.
        Ensures HOME/PATH are set so opencode finds its config and binaries.
        """
        env = os.environ.copy()
        # Ensure opencode can find its config dir and node_modules
        if "HOME" not in env:
            env["HOME"] = os.path.expanduser("~")
        name = self.llm_config.name.lower()
        if "deepseek" in name:
            env["DEEPSEEK_API_KEY"] = self.llm_config.api_key
        elif "openai" in name:
            env["OPENAI_API_KEY"] = self.llm_config.api_key
        elif "glm" in name or "zhipu" in name or "智谱" in name:
            env["GLM_API_KEY"] = self.llm_config.api_key
        else:
            # Generic: set as OPENAI_API_KEY for OpenAI-compatible providers
            env["OPENAI_API_KEY"] = self.llm_config.api_key
        return env

    def run(self, repo_path: str, prompt: str, model: str,
            timeout: int = 600) -> str:
        model_id = self._get_model_id(model)
        env = self._get_env()

        result = subprocess.run(
            ["opencode", "run", "--format", "json", "--model", model_id, prompt],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return result.stdout
