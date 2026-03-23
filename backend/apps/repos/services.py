import logging

import requests
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
