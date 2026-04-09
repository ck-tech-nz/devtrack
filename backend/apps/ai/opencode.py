import os
import shutil
import subprocess


def _opencode_bin() -> str | None:
    """Return the opencode binary path from OPENCODE_PATH env var, or locate it in PATH."""
    path = os.environ.get("OPENCODE_PATH", "").strip()
    if path:
        return path if os.path.isfile(path) else None
    return shutil.which("opencode")


class OpenCodeRunner:
    def __init__(self, llm_config):
        self.llm_config = llm_config

    def check_health(self) -> bool:
        return _opencode_bin() is not None

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

        bin_path = _opencode_bin()
        if not bin_path:
            raise FileNotFoundError(
                "opencode 未安装。请设置 OPENCODE_PATH 环境变量指向 opencode 可执行文件路径。"
            )

        # Pass prompt via stdin to avoid CLI argument length/escaping issues
        # and to keep error messages clean on timeout
        result = subprocess.run(
            [bin_path, "run", "--format", "json", "--model", model_id],
            input=prompt,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return result.stdout
