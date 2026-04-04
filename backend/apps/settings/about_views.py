import os
import platform
import subprocess

import django
import rest_framework
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.settings import BASE_DIR


def _read_version_file():
    """读取 CI 生成的 VERSION 文件"""
    version_file = BASE_DIR / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return None


def _get_git_hash():
    """获取当前 git commit hash"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=BASE_DIR,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _get_pyproject_version():
    """从 pyproject.toml 读取版本号"""
    pyproject = BASE_DIR / "pyproject.toml"
    if pyproject.exists():
        for line in pyproject.read_text().splitlines():
            if line.strip().startswith("version"):
                return line.split("=")[1].strip().strip('"').strip("'")
    return None


class AboutView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        build_version = _read_version_file()
        git_hash = None
        build_date = None

        if build_version and "-" in build_version:
            # 格式: YYYY-MM-DD-HH:MM:SS-SHORT_SHA
            parts = build_version.rsplit("-", 1)
            if len(parts) == 2:
                build_date = parts[0]
                git_hash = parts[1]

        if not git_hash:
            git_hash = _get_git_hash()

        return Response(
            {
                "backend": {
                    "version": _get_pyproject_version() or "0.1.0",
                    "git_hash": git_hash,
                    "build_date": build_date,
                    "python_version": platform.python_version(),
                    "django_version": django.get_version(),
                    "drf_version": rest_framework.VERSION,
                },
                "environment": {
                    "debug": os.environ.get("DJANGO_DEBUG", "True").lower()
                    in ("true", "1"),
                    "database": os.environ.get("DB_HOST", "127.0.0.1")
                    + ":"
                    + os.environ.get("DB_PORT", "25432"),
                },
            }
        )
