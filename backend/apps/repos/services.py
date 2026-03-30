import logging
import os
import shutil
import stat
import subprocess
from subprocess import CalledProcessError
import tempfile

import requests
from django.conf import settings as django_settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Repo, GitHubIssue

logger = logging.getLogger(__name__)


class GitHubSyncService:
    GITHUB_API = "https://api.github.com"
    PER_PAGE = 100

    def sync_repo(self, repo: Repo) -> None:
        headers = self._headers(repo)
        page = 1
        while True:
            response = requests.get(
                f"{self.GITHUB_API}/repos/{repo.full_name}/issues",
                headers=headers,
                params={"state": "all", "per_page": self.PER_PAGE, "page": page},
                timeout=30,
            )
            response.raise_for_status()
            items = response.json()
            if not items:
                break
            for item in items:
                if "pull_request" in item:
                    continue
                github_updated_at = parse_datetime(item["updated_at"])
                existing = GitHubIssue.objects.filter(
                    repo=repo, github_id=item["number"]
                ).first()
                if existing and existing.github_updated_at == github_updated_at:
                    continue
                GitHubIssue.objects.update_or_create(
                    repo=repo,
                    github_id=item["number"],
                    defaults={
                        "title": item["title"],
                        "body": item.get("body") or "",
                        "state": item["state"],
                        "labels": [label["name"] for label in item.get("labels", [])],
                        "assignees": [a["login"] for a in item.get("assignees", [])],
                        "github_created_at": parse_datetime(item["created_at"]),
                        "github_updated_at": github_updated_at,
                        "github_closed_at": parse_datetime(item["closed_at"]) if item.get("closed_at") else None,
                        "synced_at": timezone.now(),
                    },
                )
            page += 1
        repo.last_synced_at = timezone.now()
        repo.save(update_fields=["last_synced_at"])

    def _headers(self, repo: Repo) -> dict:
        return {
            "Authorization": f"Bearer {repo.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def create_issue(self, repo: Repo, title: str, body: str = "") -> GitHubIssue:
        """在 GitHub 上创建 issue 并同步到本地。"""
        response = requests.post(
            f"{self.GITHUB_API}/repos/{repo.full_name}/issues",
            headers=self._headers(repo),
            json={"title": title, "body": body},
            timeout=30,
        )
        response.raise_for_status()
        item = response.json()
        gh_issue, _ = GitHubIssue.objects.update_or_create(
            repo=repo,
            github_id=item["number"],
            defaults={
                "title": item["title"],
                "body": item.get("body") or "",
                "state": item["state"],
                "labels": [l["name"] for l in item.get("labels", [])],
                "assignees": [a["login"] for a in item.get("assignees", [])],
                "github_created_at": parse_datetime(item["created_at"]),
                "github_updated_at": parse_datetime(item["updated_at"]),
                "github_closed_at": None,
                "synced_at": timezone.now(),
            },
        )
        return gh_issue

    def close_issue(self, gh_issue: GitHubIssue) -> None:
        """关闭 GitHub 上的 issue。"""
        repo = gh_issue.repo
        response = requests.patch(
            f"{self.GITHUB_API}/repos/{repo.full_name}/issues/{gh_issue.github_id}",
            headers=self._headers(repo),
            json={"state": "closed"},
            timeout=30,
        )
        response.raise_for_status()
        gh_issue.state = GitHubIssue.STATE_CLOSED
        gh_issue.github_closed_at = timezone.now()
        gh_issue.synced_at = timezone.now()
        gh_issue.save(update_fields=["state", "github_closed_at", "synced_at"])

    def sync_all(self) -> None:
        for repo in Repo.objects.exclude(github_token=""):
            try:
                self.sync_repo(repo)
            except Exception:
                logger.exception("Failed to sync %s", repo.full_name)


class RepoCloneService:
    def clone_or_pull(self, repo, branch=None):
        repo.clone_status = "cloning"
        repo.clone_error = ""
        repo.save(update_fields=["clone_status", "clone_error"])

        askpass_path = None
        try:
            local_path = repo.local_path
            env, askpass_path = self._make_askpass(repo.github_token)

            # 清理残留的损坏目录（上次克隆失败留下的）
            if os.path.exists(local_path):
                check = subprocess.run(
                    ["git", "-C", local_path, "rev-parse", "HEAD"],
                    capture_output=True, text=True, timeout=10,
                )
                if check.returncode != 0:
                    shutil.rmtree(local_path)

            if not os.path.exists(local_path):
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                clone_url = repo.url if repo.url.endswith(".git") else f"{repo.url}.git"
                subprocess.run(
                    ["git", "clone", clone_url, local_path],
                    env=env, capture_output=True, text=True,
                    timeout=300, check=True,
                )
            else:
                subprocess.run(
                    ["git", "-C", local_path, "fetch", "--all"],
                    env=env, capture_output=True, text=True,
                    timeout=300, check=True,
                )
                target = branch or self._detect_default_branch(local_path) or repo.default_branch or "main"
                subprocess.run(
                    ["git", "-C", local_path, "reset", "--hard", f"origin/{target}"],
                    capture_output=True, text=True, timeout=60, check=True,
                )

            # 检测并更新实际默认分支
            detected = self._detect_default_branch(local_path)
            if detected:
                repo.default_branch = detected

            if branch:
                subprocess.run(
                    ["git", "-C", local_path, "checkout", branch],
                    env=env, capture_output=True, text=True,
                    timeout=60, check=True,
                )
                repo.current_branch = branch
            else:
                repo.current_branch = repo.default_branch or "main"

            repo.clone_status = "cloned"
            repo.cloned_at = timezone.now()
            repo.save(update_fields=["clone_status", "clone_error", "current_branch", "cloned_at", "default_branch"])
        except CalledProcessError as e:
            repo.clone_status = "failed"
            repo.clone_error = e.stderr or str(e)
            repo.save(update_fields=["clone_status", "clone_error"])
        except Exception as e:
            repo.clone_status = "failed"
            repo.clone_error = str(e)
            repo.save(update_fields=["clone_status", "clone_error"])
        finally:
            self._cleanup_askpass(askpass_path)

    def get_log(self, repo, limit=50):
        local_path = repo.local_path
        if not os.path.exists(local_path):
            return []
        result = subprocess.run(
            ["git", "-C", local_path, "log",
             "--format=%H%x00%an%x00%aI%x00%s", f"-n{limit}"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return []
        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\x00")
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3],
                })
        return commits

    def get_branches(self, repo):
        local_path = repo.local_path
        if not os.path.exists(local_path):
            return []
        result = subprocess.run(
            ["git", "-C", local_path, "branch", "-r",
             "--format=%(refname:short)"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return []
        return [b.strip() for b in result.stdout.strip().split("\n") if b.strip()]

    @staticmethod
    def _detect_default_branch(local_path):
        """从本地仓库检测远程默认分支。"""
        result = subprocess.run(
            ["git", "-C", local_path, "symbolic-ref", "refs/remotes/origin/HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            ref = result.stdout.strip()
            return ref.split("/")[-1] if "/" in ref else None
        result = subprocess.run(
            ["git", "-C", local_path, "symbolic-ref", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        for candidate in ("main", "master", "develop"):
            result = subprocess.run(
                ["git", "-C", local_path, "rev-parse", "--verify", f"origin/{candidate}"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return candidate
        return None

    @staticmethod
    def _make_askpass(token):
        env = os.environ.copy()
        if not token:
            return env, None
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False)
        f.write(f"#!/bin/sh\necho {token}\n")
        f.close()
        os.chmod(f.name, stat.S_IRWXU)
        env["GIT_ASKPASS"] = f.name
        env["GIT_TERMINAL_PROMPT"] = "0"
        return env, f.name

    @staticmethod
    def _cleanup_askpass(askpass_path):
        if askpass_path:
            try:
                os.unlink(askpass_path)
            except OSError:
                pass
