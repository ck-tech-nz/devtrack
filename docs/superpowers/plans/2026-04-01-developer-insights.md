# Developer Insights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "开发者洞察" tab to the repo detail page that shows per-developer four-dimension capability assessments (贡献量/效率/能力/质量) based on persisted git commit data.

**Architecture:** New `Commit` and `GitAuthorAlias` models in the repos app store parsed git log data. A `DeveloperInsightsService` computes four-dimension scores (0-100) per author using percentile ranking. The frontend adds a third tab to the repo detail page with team overview (developer cards with score bars) and individual detail view (radar chart + metric breakdown).

**Tech Stack:** Django models + DRF APIView, pytest + factory_boy, Nuxt 4 + ECharts radar chart + Nuxt UI components

---

### Task 1: Commit and GitAuthorAlias Models

**Files:**
- Modify: `backend/apps/repos/models.py`
- Create: `backend/apps/repos/migrations/XXXX_add_commit_and_gitauthoralias.py` (auto-generated)

- [ ] **Step 1: Add Commit model to models.py**

Add after the `GitHubIssue` class:

```python
class Commit(models.Model):
    repo = models.ForeignKey(Repo, on_delete=models.CASCADE, related_name="commits")
    hash = models.CharField(max_length=40, verbose_name="提交哈希")
    author_name = models.CharField(max_length=200, verbose_name="作者名")
    author_email = models.CharField(max_length=254, verbose_name="作者邮箱")
    date = models.DateTimeField(verbose_name="提交时间")
    message = models.TextField(verbose_name="提交信息")
    additions = models.IntegerField(default=0, verbose_name="新增行数")
    deletions = models.IntegerField(default=0, verbose_name="删除行数")
    files_changed = models.JSONField(default=list, verbose_name="变更文件")

    class Meta:
        verbose_name = "提交记录"
        verbose_name_plural = "提交记录"
        unique_together = ("repo", "hash")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.hash[:7]} {self.message[:50]}"
```

- [ ] **Step 2: Add GitAuthorAlias model to models.py**

Add after the `Commit` class. Import `settings` at the top of the file:

```python
from django.conf import settings as django_settings
```

(This import already exists. Add the `AUTH_USER_MODEL` import via `settings`.)

```python
class GitAuthorAlias(models.Model):
    repo = models.ForeignKey(Repo, on_delete=models.CASCADE, related_name="author_aliases")
    author_email = models.CharField(max_length=254, verbose_name="作者邮箱")
    author_name = models.CharField(max_length=200, verbose_name="作者名")
    user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="git_aliases",
        verbose_name="关联用户",
    )

    class Meta:
        verbose_name = "Git 作者映射"
        verbose_name_plural = "Git 作者映射"
        unique_together = ("repo", "author_email")

    def __str__(self):
        label = self.user.name if self.user else "未关联"
        return f"{self.author_name} <{self.author_email}> → {label}"
```

- [ ] **Step 3: Generate and apply migration**

Run:
```bash
cd backend && uv run python manage.py makemigrations repos
```
Expected: creates a migration file adding `Commit` and `GitAuthorAlias` tables.

```bash
uv run python manage.py migrate
```
Expected: `Applying repos.XXXX_add_commit_and_gitauthoralias... OK`

- [ ] **Step 4: Register in admin**

Add to `backend/apps/repos/admin.py`:

```python
from .models import Repo, GitHubIssue, Commit, GitAuthorAlias


@admin.register(Commit)
class CommitAdmin(ModelAdmin):
    list_display = ("repo", "hash_short", "author_name", "date", "message_short")
    list_filter = ("repo",)
    search_fields = ("hash", "author_name", "message")
    readonly_fields = (
        "repo", "hash", "author_name", "author_email", "date",
        "message", "additions", "deletions", "files_changed",
    )

    @admin.display(description="哈希")
    def hash_short(self, obj):
        return obj.hash[:7]

    @admin.display(description="信息")
    def message_short(self, obj):
        return obj.message[:60]


@admin.register(GitAuthorAlias)
class GitAuthorAliasAdmin(ModelAdmin):
    list_display = ("repo", "author_name", "author_email", "user")
    list_filter = ("repo",)
    search_fields = ("author_name", "author_email")
    autocomplete_fields = ("user",)
```

- [ ] **Step 5: Commit**

```bash
git add backend/apps/repos/models.py backend/apps/repos/admin.py backend/apps/repos/migrations/
git commit -m "feat(repos): add Commit and GitAuthorAlias models"
```

---

### Task 2: Commit Sync Service

**Files:**
- Modify: `backend/apps/repos/services.py`
- Test: `backend/tests/test_commit_sync.py`

- [ ] **Step 1: Write the failing test for sync_commits**

Create `backend/tests/test_commit_sync.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from apps.repos.models import Commit, GitAuthorAlias
from apps.repos.services import RepoCloneService
from tests.factories import RepoFactory, UserFactory

pytestmark = pytest.mark.django_db

GIT_LOG_OUTPUT = (
    "abc1234567890abcdef1234567890abcdef123456\x00dev@example.com\x00Dev One\x002026-03-30T10:00:00+08:00\x00feat(ui): add dashboard\n"
    " src/ui/dashboard.vue | 80 ++++++\n"
    " src/ui/sidebar.vue   | 30 +++\n"
    " src/api/routes.py    | 40 ++--\n"
    " 3 files changed, 120 insertions(+), 30 deletions(-)\n"
    "\n"
    "def7890abcdef1234567890abcdef1234567890abcd\x00dev@example.com\x00Dev One\x002026-03-29T09:00:00+08:00\x00fix(api): resolve 500 error\n"
    " src/api/views.py | 7 +++--\n"
    " 1 file changed, 5 insertions(+), 2 deletions(-)\n"
    "\n"
    "1111111111111111111111111111111111111111\x00other@test.com\x00Other Dev\x002026-03-28T08:00:00+08:00\x00chore: update deps\n"
    " requirements.txt | 10 ++++----\n"
    " package.json     | 8 +++---\n"
    " 2 files changed, 10 insertions(+), 8 deletions(-)\n"
    "\n"
)


class TestSyncCommits:
    def test_creates_commits_and_aliases(self):
        repo = RepoFactory(clone_status="cloned")

        def fake_run(cmd, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            # cmd is a list; check if any element starts with --format
            if any(str(c).startswith("--format") for c in cmd):
                mock.stdout = GIT_LOG_OUTPUT
            else:
                mock.stdout = ""
            return mock

        with patch("apps.repos.services.subprocess.run", side_effect=fake_run):
            with patch("apps.repos.services.os.path.exists", return_value=True):
                RepoCloneService().sync_commits(repo)

        assert Commit.objects.filter(repo=repo).count() == 3
        assert GitAuthorAlias.objects.filter(repo=repo).count() == 2

        c1 = Commit.objects.get(repo=repo, hash="abc1234567890abcdef1234567890abcdef123456")
        assert c1.author_email == "dev@example.com"
        assert c1.message == "feat(ui): add dashboard"
        assert c1.additions == 120
        assert c1.deletions == 30

    def test_skips_existing_commits(self):
        repo = RepoFactory(clone_status="cloned")
        Commit.objects.create(
            repo=repo,
            hash="abc1234567890abcdef1234567890abcdef123456",
            author_name="Dev One",
            author_email="dev@example.com",
            date="2026-03-30T10:00:00+08:00",
            message="feat(ui): add dashboard",
        )

        def fake_run(cmd, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = GIT_LOG_OUTPUT
            return mock

        with patch("apps.repos.services.subprocess.run", side_effect=fake_run):
            with patch("apps.repos.services.os.path.exists", return_value=True):
                RepoCloneService().sync_commits(repo)

        assert Commit.objects.filter(repo=repo).count() == 3

    def test_auto_matches_user_by_email(self):
        user = UserFactory(email="dev@example.com")
        repo = RepoFactory(clone_status="cloned")

        def fake_run(cmd, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = GIT_LOG_OUTPUT
            return mock

        with patch("apps.repos.services.subprocess.run", side_effect=fake_run):
            with patch("apps.repos.services.os.path.exists", return_value=True):
                RepoCloneService().sync_commits(repo)

        alias = GitAuthorAlias.objects.get(repo=repo, author_email="dev@example.com")
        assert alias.user == user
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_commit_sync.py -v`
Expected: FAIL — `AttributeError: 'RepoCloneService' object has no attribute 'sync_commits'`

- [ ] **Step 3: Implement sync_commits in RepoCloneService**

Add to `backend/apps/repos/services.py`, import the new models at the top:

```python
from .models import Repo, GitHubIssue, Commit, GitAuthorAlias
```

Add `get_user_model` import:

```python
from django.contrib.auth import get_user_model
```

Add method to `RepoCloneService`:

```python
    def sync_commits(self, repo):
        """Parse git log --stat and persist Commit + GitAuthorAlias records."""
        local_path = repo.local_path
        if not os.path.exists(local_path):
            return

        # Get existing hashes to skip
        existing_hashes = set(
            Commit.objects.filter(repo=repo).values_list("hash", flat=True)
        )

        result = subprocess.run(
            [
                "git", "-C", local_path, "log",
                "--format=%H%x00%ae%x00%an%x00%aI%x00%s",
                "--stat",
            ],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            logger.warning("git log failed for %s: %s", repo.full_name, result.stderr)
            return

        # Parse git log --stat output
        commits_data = self._parse_git_log_stat(result.stdout)

        User = get_user_model()
        email_to_user = {}
        new_commits = []

        for entry in commits_data:
            if entry["hash"] in existing_hashes:
                continue
            new_commits.append(
                Commit(
                    repo=repo,
                    hash=entry["hash"],
                    author_email=entry["author_email"],
                    author_name=entry["author_name"],
                    date=entry["date"],
                    message=entry["message"],
                    additions=entry["additions"],
                    deletions=entry["deletions"],
                    files_changed=entry["files_changed"],
                )
            )

        if new_commits:
            Commit.objects.bulk_create(new_commits, ignore_conflicts=True)

        # Sync GitAuthorAlias
        unique_authors = (
            Commit.objects.filter(repo=repo)
            .values("author_email", "author_name")
            .distinct()
        )
        for author in unique_authors:
            alias, created = GitAuthorAlias.objects.get_or_create(
                repo=repo,
                author_email=author["author_email"],
                defaults={"author_name": author["author_name"]},
            )
            if created and not alias.user:
                matched_user = User.objects.filter(email=author["author_email"]).first()
                if matched_user:
                    alias.user = matched_user
                    alias.save(update_fields=["user"])

    @staticmethod
    def _parse_git_log_stat(output):
        """Parse combined git log --format + --stat output into structured data."""
        import re
        entries = []
        lines = output.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            if not line or "\x00" not in line:
                i += 1
                continue
            parts = line.split("\x00")
            if len(parts) != 5:
                i += 1
                continue
            hash_val, author_email, author_name, date, message = parts
            additions = 0
            deletions = 0
            files_changed = []
            i += 1
            # Parse --stat lines until next commit or blank
            while i < len(lines):
                stat_line = lines[i]
                if not stat_line.strip():
                    i += 1
                    break
                if "\x00" in stat_line:
                    break  # Next commit header
                # Match stat summary line: " N files changed, X insertions(+), Y deletions(-)"
                summary_match = re.match(
                    r"\s*\d+ files? changed(?:,\s*(\d+) insertions?\(\+\))?(?:,\s*(\d+) deletions?\(-\))?",
                    stat_line,
                )
                if summary_match:
                    additions = int(summary_match.group(1) or 0)
                    deletions = int(summary_match.group(2) or 0)
                    i += 1
                    continue
                # Match individual file stat: " path/to/file | N ++--"
                file_match = re.match(r"\s*(.+?)\s+\|", stat_line)
                if file_match:
                    files_changed.append(file_match.group(1).strip())
                i += 1

            entries.append({
                "hash": hash_val,
                "author_email": author_email,
                "author_name": author_name,
                "date": date,
                "message": message,
                "additions": additions,
                "deletions": deletions,
                "files_changed": files_changed,
            })
        return entries
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_commit_sync.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Hook sync_commits into clone_or_pull**

In `RepoCloneService.clone_or_pull()`, add the call right after `repo.clone_status = "cloned"` and `repo.save(...)` — before the except blocks:

```python
            # After repo.save(update_fields=...) on line ~179
            # Sync commits after successful clone/pull
            try:
                self.sync_commits(repo)
            except Exception:
                logger.exception("sync_commits failed for %s", repo.full_name)
```

- [ ] **Step 6: Commit**

```bash
cd backend
git add apps/repos/services.py tests/test_commit_sync.py
git commit -m "feat(repos): add sync_commits service with git log --stat parsing"
```

---

### Task 3: Developer Insights Service (Scoring Engine)

**Files:**
- Create: `backend/apps/repos/insights.py`
- Test: `backend/tests/test_developer_insights.py`

- [ ] **Step 1: Write the failing test for score calculation**

Create `backend/tests/test_developer_insights.py`:

```python
import pytest
from datetime import timedelta
from django.utils import timezone
from apps.repos.insights import DeveloperInsightsService
from apps.repos.models import Commit, GitAuthorAlias
from tests.factories import RepoFactory, UserFactory

pytestmark = pytest.mark.django_db


def _create_commits(repo, author_email, author_name, messages, base_date=None):
    """Helper to create commits for a given author."""
    if base_date is None:
        base_date = timezone.now()
    commits = []
    for i, msg in enumerate(messages):
        commits.append(Commit(
            repo=repo,
            hash=f"{author_email[:4]}{i:036d}",
            author_email=author_email,
            author_name=author_name,
            date=base_date - timedelta(days=i),
            message=msg,
            additions=50 + i * 10,
            deletions=10 + i * 5,
            files_changed=[f"src/module{i % 3}/file{i}.py"],
        ))
    Commit.objects.bulk_create(commits)


class TestDeveloperInsightsService:
    def test_team_overview_returns_all_authors(self):
        repo = RepoFactory(clone_status="cloned")
        _create_commits(repo, "a@test.com", "Alice", ["feat: add login", "fix: typo"])
        _create_commits(repo, "b@test.com", "Bob", ["feat: add dashboard"])
        GitAuthorAlias.objects.create(repo=repo, author_email="a@test.com", author_name="Alice")
        GitAuthorAlias.objects.create(repo=repo, author_email="b@test.com", author_name="Bob")

        result = DeveloperInsightsService().team_overview(repo, days=90)
        assert len(result) == 2
        emails = [r["author_email"] for r in result]
        assert "a@test.com" in emails
        assert "b@test.com" in emails

    def test_scores_are_0_to_100(self):
        repo = RepoFactory(clone_status="cloned")
        _create_commits(repo, "a@test.com", "Alice", [
            "feat: one", "fix: two", "refactor: three", "chore: four", "docs: five"
        ])
        _create_commits(repo, "b@test.com", "Bob", ["feat: only one"])
        GitAuthorAlias.objects.create(repo=repo, author_email="a@test.com", author_name="Alice")
        GitAuthorAlias.objects.create(repo=repo, author_email="b@test.com", author_name="Bob")

        result = DeveloperInsightsService().team_overview(repo, days=90)
        for dev in result:
            for dim in ["contribution", "efficiency", "capability", "quality"]:
                score = dev["scores"][dim]
                assert 0 <= score <= 100, f"{dev['author_name']}.{dim} = {score}"

    def test_single_developer_gets_50(self):
        repo = RepoFactory(clone_status="cloned")
        _create_commits(repo, "solo@test.com", "Solo", ["feat: init", "fix: bug"])
        GitAuthorAlias.objects.create(repo=repo, author_email="solo@test.com", author_name="Solo")

        result = DeveloperInsightsService().team_overview(repo, days=90)
        assert len(result) == 1
        for dim in ["contribution", "efficiency", "capability", "quality"]:
            assert result[0]["scores"][dim] == 50

    def test_individual_detail(self):
        repo = RepoFactory(clone_status="cloned")
        _create_commits(repo, "a@test.com", "Alice", [
            "feat(ui): login page", "fix(api): auth error", "refactor: cleanup"
        ])
        alias = GitAuthorAlias.objects.create(repo=repo, author_email="a@test.com", author_name="Alice")

        result = DeveloperInsightsService().individual_detail(repo, alias.id, days=90)
        assert result["author_name"] == "Alice"
        assert "scores" in result
        assert "details" in result
        assert "commit_types" in result["details"]

    def test_days_filter(self):
        repo = RepoFactory(clone_status="cloned")
        now = timezone.now()
        # Recent commit
        Commit.objects.create(
            repo=repo, hash="a" * 40, author_email="a@test.com", author_name="Alice",
            date=now - timedelta(days=5), message="feat: recent", additions=10, deletions=5,
        )
        # Old commit
        Commit.objects.create(
            repo=repo, hash="b" * 40, author_email="a@test.com", author_name="Alice",
            date=now - timedelta(days=100), message="feat: old", additions=10, deletions=5,
        )
        GitAuthorAlias.objects.create(repo=repo, author_email="a@test.com", author_name="Alice")

        result = DeveloperInsightsService().team_overview(repo, days=30)
        assert result[0]["stats"]["commit_count"] == 1

    def test_unlinked_authors_returned(self):
        repo = RepoFactory(clone_status="cloned")
        _create_commits(repo, "a@test.com", "Alice", ["feat: one"])
        GitAuthorAlias.objects.create(repo=repo, author_email="a@test.com", author_name="Alice")
        user = UserFactory(email="b@test.com")
        _create_commits(repo, "b@test.com", "Bob", ["feat: two"])
        GitAuthorAlias.objects.create(repo=repo, author_email="b@test.com", author_name="Bob", user=user)

        service = DeveloperInsightsService()
        unlinked = service.unlinked_authors(repo)
        assert len(unlinked) == 1
        assert unlinked[0]["author_email"] == "a@test.com"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_developer_insights.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.repos.insights'`

- [ ] **Step 3: Implement DeveloperInsightsService**

Create `backend/apps/repos/insights.py`:

```python
import math
import re
from datetime import timedelta

from django.db.models import Count, Sum, Q
from django.utils import timezone

from .models import Commit, GitAuthorAlias

CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|refactor|chore|docs|style|test|perf|ci|build)(\(.+\))?[!]?:\s.+"
)
COMMIT_TYPE_RE = re.compile(r"^(feat|fix|refactor|chore|docs|style|test|perf|ci|build)")


class DeveloperInsightsService:
    def team_overview(self, repo, days=90):
        """Return list of developer score cards for team overview."""
        cutoff = self._cutoff(days)
        commits = Commit.objects.filter(repo=repo)
        if cutoff:
            commits = commits.filter(date__gte=cutoff)

        aliases = GitAuthorAlias.objects.filter(repo=repo).select_related("user")
        alias_map = {a.author_email: a for a in aliases}

        # Group commits by author email
        author_emails = commits.values_list("author_email", flat=True).distinct()
        raw_metrics = {}
        for email in author_emails:
            author_commits = commits.filter(author_email=email)
            raw_metrics[email] = self._compute_raw_metrics(author_commits, days)

        # Compute percentile scores
        results = []
        for email, metrics in raw_metrics.items():
            alias = alias_map.get(email)
            scores = self._percentile_scores(email, raw_metrics)
            results.append({
                "alias_id": alias.id if alias else None,
                "author_email": email,
                "author_name": metrics["author_name"],
                "user_id": alias.user_id if alias and alias.user else None,
                "user_name": alias.user.name if alias and alias.user else None,
                "scores": scores,
                "stats": {
                    "commit_count": metrics["commit_count"],
                    "additions": metrics["additions"],
                    "deletions": metrics["deletions"],
                },
            })
        return sorted(results, key=lambda x: -x["stats"]["commit_count"])

    def individual_detail(self, repo, alias_id, days=90):
        """Return detailed metrics for a single developer."""
        alias = GitAuthorAlias.objects.select_related("user").get(id=alias_id, repo=repo)
        cutoff = self._cutoff(days)
        all_commits = Commit.objects.filter(repo=repo)
        if cutoff:
            all_commits = all_commits.filter(date__gte=cutoff)

        author_commits = all_commits.filter(author_email=alias.author_email)

        # Compute raw metrics for all authors (for percentile context)
        author_emails = all_commits.values_list("author_email", flat=True).distinct()
        raw_metrics = {}
        for email in author_emails:
            raw_metrics[email] = self._compute_raw_metrics(
                all_commits.filter(author_email=email), days
            )

        scores = self._percentile_scores(alias.author_email, raw_metrics)
        my_metrics = raw_metrics[alias.author_email]

        return {
            "alias_id": alias.id,
            "author_email": alias.author_email,
            "author_name": alias.author_name,
            "user_id": alias.user_id if alias.user else None,
            "user_name": alias.user.name if alias.user else None,
            "scores": scores,
            "details": {
                "commit_count": my_metrics["commit_count"],
                "additions": my_metrics["additions"],
                "deletions": my_metrics["deletions"],
                "commit_frequency": round(my_metrics["commit_frequency"], 1),
                "active_days_ratio": round(my_metrics["active_days_ratio"] * 100, 1),
                "directory_count": my_metrics["directory_count"],
                "commit_types": my_metrics["commit_types"],
                "fix_ratio": round(my_metrics["fix_ratio"] * 100, 1),
                "conventional_ratio": round(my_metrics["conventional_ratio"] * 100, 1),
            },
        }

    def unlinked_authors(self, repo):
        """Return GitAuthorAlias entries with no linked user."""
        return list(
            GitAuthorAlias.objects.filter(repo=repo, user__isnull=True)
            .values("id", "author_email", "author_name")
        )

    # --- Private helpers ---

    def _cutoff(self, days):
        if days is None or days == 0:
            return None
        return timezone.now() - timedelta(days=days)

    def _compute_raw_metrics(self, commits_qs, days):
        """Compute raw metric values for a set of commits belonging to one author."""
        commit_list = list(commits_qs.values(
            "author_name", "date", "message", "additions", "deletions", "files_changed"
        ))
        if not commit_list:
            return self._empty_metrics()

        count = len(commit_list)
        additions = sum(c["additions"] for c in commit_list)
        deletions = sum(c["deletions"] for c in commit_list)

        # Efficiency: frequency and active days
        dates = [c["date"].date() for c in commit_list]
        unique_dates = set(dates)
        active_days = len(unique_dates)
        total_days = days if days else max((max(dates) - min(dates)).days, 1)
        if total_days == 0:
            total_days = 1
        weeks = max(total_days / 7, 1)
        commit_frequency = count / weeks
        active_days_ratio = active_days / total_days

        # Capability: directory breadth
        all_files = []
        for c in commit_list:
            all_files.extend(c["files_changed"] or [])
        top_dirs = set()
        for f in all_files:
            parts = f.split("/")
            if len(parts) > 1:
                top_dirs.add(parts[0])
            else:
                top_dirs.add("root")
        directory_count = len(top_dirs)

        # Capability: commit type diversity (Shannon entropy)
        commit_types = {}
        for c in commit_list:
            m = COMMIT_TYPE_RE.match(c["message"])
            ctype = m.group(1) if m else "other"
            commit_types[ctype] = commit_types.get(ctype, 0) + 1
        type_entropy = self._shannon_entropy(commit_types, count)

        # Quality: fix ratio, conventional commits ratio
        fix_count = commit_types.get("fix", 0)
        fix_ratio = fix_count / count if count else 0
        conventional_count = sum(1 for c in commit_list if CONVENTIONAL_RE.match(c["message"]))
        conventional_ratio = conventional_count / count if count else 0

        return {
            "author_name": commit_list[0]["author_name"],
            "commit_count": count,
            "additions": additions,
            "deletions": deletions,
            "lines_changed": additions + deletions,
            "commit_frequency": commit_frequency,
            "active_days_ratio": active_days_ratio,
            "directory_count": directory_count,
            "type_entropy": type_entropy,
            "commit_types": commit_types,
            "fix_ratio": fix_ratio,
            "conventional_ratio": conventional_ratio,
        }

    def _empty_metrics(self):
        return {
            "author_name": "",
            "commit_count": 0, "additions": 0, "deletions": 0, "lines_changed": 0,
            "commit_frequency": 0, "active_days_ratio": 0,
            "directory_count": 0, "type_entropy": 0, "commit_types": {},
            "fix_ratio": 0, "conventional_ratio": 0,
        }

    def _percentile_scores(self, target_email, raw_metrics):
        """Compute four-dimension 0-100 scores using percentile ranking."""
        n = len(raw_metrics)
        if n <= 1:
            return {"contribution": 50, "efficiency": 50, "capability": 50, "quality": 50}

        def percentile(values, target_val):
            below = sum(1 for v in values if v < target_val)
            return round(below / (n - 1) * 100)

        target = raw_metrics[target_email]
        all_vals = list(raw_metrics.values())

        # Contribution: 50% commit_count + 50% lines_changed
        contrib_count = percentile([m["commit_count"] for m in all_vals], target["commit_count"])
        contrib_lines = percentile([m["lines_changed"] for m in all_vals], target["lines_changed"])
        contribution = round(contrib_count * 0.5 + contrib_lines * 0.5)

        # Efficiency: 50% commit_frequency + 50% active_days_ratio
        eff_freq = percentile([m["commit_frequency"] for m in all_vals], target["commit_frequency"])
        eff_active = percentile([m["active_days_ratio"] for m in all_vals], target["active_days_ratio"])
        efficiency = round(eff_freq * 0.5 + eff_active * 0.5)

        # Capability: 50% directory_count + 50% type_entropy
        cap_dirs = percentile([m["directory_count"] for m in all_vals], target["directory_count"])
        cap_entropy = percentile([m["type_entropy"] for m in all_vals], target["type_entropy"])
        capability = round(cap_dirs * 0.5 + cap_entropy * 0.5)

        # Quality: 50% (1 - fix_ratio) + 50% conventional_ratio
        qual_fix = percentile(
            [1 - m["fix_ratio"] for m in all_vals], 1 - target["fix_ratio"]
        )
        qual_conv = percentile(
            [m["conventional_ratio"] for m in all_vals], target["conventional_ratio"]
        )
        quality = round(qual_fix * 0.5 + qual_conv * 0.5)

        return {
            "contribution": contribution,
            "efficiency": efficiency,
            "capability": capability,
            "quality": quality,
        }

    @staticmethod
    def _shannon_entropy(type_counts, total):
        """Calculate Shannon entropy for commit type distribution."""
        if total == 0:
            return 0
        entropy = 0
        for count in type_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        return entropy
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_developer_insights.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
cd backend
git add apps/repos/insights.py tests/test_developer_insights.py
git commit -m "feat(repos): add DeveloperInsightsService with four-dimension scoring"
```

---

### Task 4: API Views, Serializers, and URLs

**Files:**
- Modify: `backend/apps/repos/serializers.py`
- Modify: `backend/apps/repos/views.py`
- Modify: `backend/apps/repos/urls.py`
- Test: `backend/tests/test_insights_api.py`

- [ ] **Step 1: Write the failing API tests**

Create `backend/tests/test_insights_api.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta
from apps.repos.models import Commit, GitAuthorAlias
from tests.factories import RepoFactory, UserFactory

pytestmark = pytest.mark.django_db


def _seed(repo, email="dev@test.com", name="Dev", count=3):
    for i in range(count):
        Commit.objects.create(
            repo=repo,
            hash=f"{email[:3]}{i:037d}",
            author_email=email,
            author_name=name,
            date=timezone.now() - timedelta(days=i),
            message=f"feat: commit {i}",
            additions=10 * (i + 1),
            deletions=5 * (i + 1),
            files_changed=[f"src/mod{i}/file.py"],
        )
    GitAuthorAlias.objects.get_or_create(
        repo=repo, author_email=email, defaults={"author_name": name}
    )


class TestDeveloperInsightsListAPI:
    def test_returns_developer_list(self, auth_client):
        repo = RepoFactory(clone_status="cloned")
        _seed(repo, "a@test.com", "Alice", 5)
        _seed(repo, "b@test.com", "Bob", 3)
        response = auth_client.get(f"/api/repos/{repo.id}/developer-insights/")
        assert response.status_code == 200
        assert len(response.data["developers"]) == 2
        assert "scores" in response.data["developers"][0]

    def test_days_filter(self, auth_client):
        repo = RepoFactory(clone_status="cloned")
        _seed(repo)
        response = auth_client.get(f"/api/repos/{repo.id}/developer-insights/?days=30")
        assert response.status_code == 200

    def test_includes_unlinked_authors(self, auth_client):
        repo = RepoFactory(clone_status="cloned")
        _seed(repo)
        response = auth_client.get(f"/api/repos/{repo.id}/developer-insights/")
        assert "unlinked_count" in response.data

    def test_unauthenticated(self, api_client):
        repo = RepoFactory()
        response = api_client.get(f"/api/repos/{repo.id}/developer-insights/")
        assert response.status_code == 401


class TestDeveloperInsightsDetailAPI:
    def test_returns_individual_detail(self, auth_client):
        repo = RepoFactory(clone_status="cloned")
        _seed(repo)
        alias = GitAuthorAlias.objects.first()
        response = auth_client.get(
            f"/api/repos/{repo.id}/developer-insights/{alias.id}/"
        )
        assert response.status_code == 200
        assert "scores" in response.data
        assert "details" in response.data

    def test_404_for_wrong_alias(self, auth_client):
        repo = RepoFactory(clone_status="cloned")
        response = auth_client.get(f"/api/repos/{repo.id}/developer-insights/99999/")
        assert response.status_code == 404


class TestSyncCommitsAPI:
    def test_sync_commits_endpoint(self, auth_client):
        repo = RepoFactory(clone_status="cloned")
        with patch("apps.repos.views.RepoCloneService") as MockService:
            mock_instance = MagicMock()
            MockService.return_value = mock_instance
            response = auth_client.post(f"/api/repos/{repo.id}/sync-commits/")
        assert response.status_code == 200
        mock_instance.sync_commits.assert_called_once()

    def test_sync_404_not_cloned(self, auth_client):
        repo = RepoFactory(clone_status="not_cloned")
        response = auth_client.post(f"/api/repos/{repo.id}/sync-commits/")
        assert response.status_code == 400


class TestGitAuthorAliasPatchAPI:
    def test_link_user(self, auth_client):
        repo = RepoFactory(clone_status="cloned")
        _seed(repo)
        alias = GitAuthorAlias.objects.first()
        user = UserFactory()
        response = auth_client.patch(
            f"/api/repos/{repo.id}/git-author-aliases/{alias.id}/",
            {"user": user.id},
            format="json",
        )
        assert response.status_code == 200
        alias.refresh_from_db()
        assert alias.user == user

    def test_unlink_user(self, auth_client):
        user = UserFactory()
        repo = RepoFactory(clone_status="cloned")
        _seed(repo)
        alias = GitAuthorAlias.objects.first()
        alias.user = user
        alias.save()
        response = auth_client.patch(
            f"/api/repos/{repo.id}/git-author-aliases/{alias.id}/",
            {"user": None},
            format="json",
        )
        assert response.status_code == 200
        alias.refresh_from_db()
        assert alias.user is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_insights_api.py -v`
Expected: FAIL — 404 on all endpoints

- [ ] **Step 3: Add serializer for GitAuthorAlias**

Add to `backend/apps/repos/serializers.py`:

```python
from .models import Repo, GitHubIssue, GitAuthorAlias


class GitAuthorAliasSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True, default=None)

    class Meta:
        model = GitAuthorAlias
        fields = ["id", "author_email", "author_name", "user", "user_name"]
        read_only_fields = ["id", "author_email", "author_name"]
```

- [ ] **Step 4: Add views**

Add to `backend/apps/repos/views.py`:

```python
from .insights import DeveloperInsightsService
from .serializers import RepoSerializer, GitHubIssueBriefSerializer, GitHubIssueDetailSerializer, GitAuthorAliasSerializer
from .models import Repo, GitHubIssue, GitAuthorAlias


class DeveloperInsightsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            repo = Repo.objects.get(pk=pk)
        except Repo.DoesNotExist:
            return Response({"detail": "仓库不存在"}, status=status.HTTP_404_NOT_FOUND)
        days_param = request.query_params.get("days", "90")
        days = None if days_param == "all" else int(days_param)
        service = DeveloperInsightsService()
        developers = service.team_overview(repo, days=days)
        unlinked = service.unlinked_authors(repo)
        return Response({
            "developers": developers,
            "unlinked_count": len(unlinked),
            "unlinked_authors": unlinked,
        })


class DeveloperInsightsDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, alias_id):
        try:
            repo = Repo.objects.get(pk=pk)
        except Repo.DoesNotExist:
            return Response({"detail": "仓库不存在"}, status=status.HTTP_404_NOT_FOUND)
        try:
            days_param = request.query_params.get("days", "90")
            days = None if days_param == "all" else int(days_param)
            result = DeveloperInsightsService().individual_detail(repo, alias_id, days=days)
            return Response(result)
        except GitAuthorAlias.DoesNotExist:
            return Response({"detail": "作者不存在"}, status=status.HTTP_404_NOT_FOUND)


class SyncCommitsView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = Repo.objects.none()

    def post(self, request, pk):
        try:
            repo = Repo.objects.get(pk=pk)
        except Repo.DoesNotExist:
            return Response({"detail": "仓库不存在"}, status=status.HTTP_404_NOT_FOUND)
        if repo.clone_status != "cloned":
            return Response({"detail": "请先同步代码"}, status=status.HTTP_400_BAD_REQUEST)
        RepoCloneService().sync_commits(repo)
        return Response({"detail": "提交记录同步完成"})


class GitAuthorAliasPatchView(APIView):
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = GitAuthorAlias.objects.none()

    def patch(self, request, pk, alias_id):
        try:
            alias = GitAuthorAlias.objects.get(id=alias_id, repo_id=pk)
        except GitAuthorAlias.DoesNotExist:
            return Response({"detail": "作者映射不存在"}, status=status.HTTP_404_NOT_FOUND)
        serializer = GitAuthorAliasSerializer(alias, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
```

- [ ] **Step 5: Add URL routes**

Update `backend/apps/repos/urls.py`:

```python
from django.urls import path
from .views import (
    RepoListCreateView, RepoDetailView, GitHubIssueListView,
    RepoSyncView, GitHubIssueDetailView,
    RepoCloneView, RepoGitLogView, RepoBranchesView,
    DeveloperInsightsListView, DeveloperInsightsDetailView,
    SyncCommitsView, GitAuthorAliasPatchView,
)

urlpatterns = [
    path("", RepoListCreateView.as_view(), name="repo-list"),
    path("github-issues/", GitHubIssueListView.as_view(), name="github-issue-list"),
    path("github-issues/<int:pk>/", GitHubIssueDetailView.as_view(), name="github-issue-detail"),
    path("<int:pk>/sync/", RepoSyncView.as_view(), name="repo-sync"),
    path("<int:pk>/clone/", RepoCloneView.as_view(), name="repo-clone"),
    path("<int:pk>/git-log/", RepoGitLogView.as_view(), name="repo-git-log"),
    path("<int:pk>/branches/", RepoBranchesView.as_view(), name="repo-branches"),
    path("<int:pk>/sync-commits/", SyncCommitsView.as_view(), name="repo-sync-commits"),
    path("<int:pk>/developer-insights/", DeveloperInsightsListView.as_view(), name="developer-insights-list"),
    path("<int:pk>/developer-insights/<int:alias_id>/", DeveloperInsightsDetailView.as_view(), name="developer-insights-detail"),
    path("<int:pk>/git-author-aliases/<int:alias_id>/", GitAuthorAliasPatchView.as_view(), name="git-author-alias-patch"),
    path("<int:pk>/", RepoDetailView.as_view(), name="repo-detail"),
]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_insights_api.py -v`
Expected: All tests PASS

- [ ] **Step 7: Run all backend tests**

Run: `cd backend && uv run pytest -v`
Expected: All tests PASS (existing + new)

- [ ] **Step 8: Commit**

```bash
cd backend
git add apps/repos/serializers.py apps/repos/views.py apps/repos/urls.py tests/test_insights_api.py
git commit -m "feat(repos): add developer insights API endpoints"
```

---

### Task 5: Add Commit and GitAuthorAlias Factories

**Files:**
- Modify: `backend/tests/factories.py`

- [ ] **Step 1: Add factories**

Add to `backend/tests/factories.py`:

```python
from apps.repos.models import Repo, GitHubIssue, Commit, GitAuthorAlias
```

Update the import line, then add after `GitHubIssueFactory`:

```python
class CommitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Commit

    repo = factory.SubFactory(RepoFactory)
    hash = factory.LazyFunction(lambda: fake.sha1())
    author_name = factory.LazyFunction(lambda: fake.name())
    author_email = factory.LazyFunction(lambda: fake.email())
    date = factory.LazyFunction(tz.now)
    message = factory.LazyFunction(lambda: fake.sentence())
    additions = factory.LazyFunction(lambda: fake.random_int(1, 200))
    deletions = factory.LazyFunction(lambda: fake.random_int(0, 100))
    files_changed = factory.LazyFunction(lambda: [f"src/{fake.file_name()}"])


class GitAuthorAliasFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GitAuthorAlias

    repo = factory.SubFactory(RepoFactory)
    author_email = factory.LazyFunction(lambda: fake.email())
    author_name = factory.LazyFunction(lambda: fake.name())
    user = None
```

- [ ] **Step 2: Commit**

```bash
cd backend
git add tests/factories.py
git commit -m "feat(tests): add CommitFactory and GitAuthorAliasFactory"
```

---

### Task 6: Frontend — Radar Chart Component

**Files:**
- Create: `frontend/app/components/charts/RadarChart.vue`

- [ ] **Step 1: Create RadarChart component**

Create `frontend/app/components/charts/RadarChart.vue`:

```vue
<template>
  <div ref="chartRef" class="w-full" :style="{ height: height + 'px' }" />
</template>

<script setup lang="ts">
import * as echarts from 'echarts/core'
import { RadarChart as ERadarChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([ERadarChart, TooltipComponent, CanvasRenderer])

const props = withDefaults(defineProps<{
  indicators: { name: string; max: number }[]
  values: number[]
  height?: number
}>(), { height: 280 })

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const colorMode = useColorMode()
const isDark = computed(() => colorMode.value === 'dark')

onMounted(() => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  renderChart()
})

watch(() => [props.indicators, props.values], renderChart, { deep: true })
watch(isDark, () => renderChart())

function renderChart() {
  if (!chart) return
  const dark = isDark.value
  chart.setOption({
    tooltip: {
      backgroundColor: dark ? '#1f2937' : '#fff',
      borderColor: dark ? '#374151' : '#e5e7eb',
      textStyle: { color: dark ? '#e5e7eb' : '#374151', fontSize: 12 },
    },
    radar: {
      indicator: props.indicators,
      shape: 'polygon',
      splitNumber: 4,
      axisName: {
        color: dark ? '#9ca3af' : '#6b7280',
        fontSize: 12,
        fontWeight: 600,
      },
      splitArea: {
        areaStyle: {
          color: dark
            ? ['rgba(55,65,81,0.3)', 'rgba(55,65,81,0.15)']
            : ['rgba(241,245,249,0.8)', 'rgba(248,250,252,0.5)'],
        },
      },
      axisLine: { lineStyle: { color: dark ? '#374151' : '#e2e8f0' } },
      splitLine: { lineStyle: { color: dark ? '#374151' : '#e2e8f0' } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: props.values,
        areaStyle: { color: 'rgba(99,102,241,0.15)' },
        lineStyle: { color: '#6366f1', width: 2 },
        itemStyle: { color: '#6366f1' },
      }],
    }],
  })
}

let observer: ResizeObserver | null = null
onMounted(() => {
  if (chartRef.value) {
    observer = new ResizeObserver(() => { chart?.resize() })
    observer.observe(chartRef.value)
  }
})
onUnmounted(() => { observer?.disconnect(); chart?.dispose() })
</script>
```

- [ ] **Step 2: Commit**

```bash
cd frontend
git add app/components/charts/RadarChart.vue
git commit -m "feat(frontend): add RadarChart component using ECharts"
```

---

### Task 7: Frontend — Developer Insights Tab

**Files:**
- Modify: `frontend/app/pages/app/repos/[id]/index.vue`

This is the largest frontend task. We add the third tab with team overview and individual detail views.

- [ ] **Step 1: Add tab item and state variables**

In the `<script setup>` section of `[id]/index.vue`, add after the `gitLogLoading` state:

```typescript
// Developer insights state
const insightsData = ref<any>(null)
const insightsLoading = ref(false)
const selectedDeveloper = ref<any>(null)
const developerDetail = ref<any>(null)
const developerDetailLoading = ref(false)
const insightsDays = ref('90')
const showLinkModal = ref(false)
const allUsers = ref<any[]>([])
```

Update `tabItems`:

```typescript
const tabItems = [
  { label: 'Issues', slot: 'issues', value: 'issues' },
  { label: '提交记录', slot: 'git-log', value: 'git-log' },
  { label: '开发者洞察', slot: 'insights', value: 'insights' },
]
```

- [ ] **Step 2: Add fetch functions**

Add after `fetchGitLog()`:

```typescript
const daysOptions = [
  { label: '30天', value: '30' },
  { label: '90天', value: '90' },
  { label: '全部', value: 'all' },
]

async function fetchInsights() {
  if (repo.value?.clone_status !== 'cloned') return
  insightsLoading.value = true
  try {
    insightsData.value = await api<any>(
      `/api/repos/${route.params.id}/developer-insights/?days=${insightsDays.value}`
    )
  } catch (e) {
    console.error('Failed to load insights:', e)
  } finally {
    insightsLoading.value = false
  }
}

async function fetchDeveloperDetail(aliasId: number) {
  developerDetailLoading.value = true
  try {
    developerDetail.value = await api<any>(
      `/api/repos/${route.params.id}/developer-insights/${aliasId}/?days=${insightsDays.value}`
    )
  } catch (e) {
    console.error('Failed to load developer detail:', e)
  } finally {
    developerDetailLoading.value = false
  }
}

function selectDeveloper(dev: any) {
  selectedDeveloper.value = dev
  fetchDeveloperDetail(dev.alias_id)
}

function backToTeam() {
  selectedDeveloper.value = null
  developerDetail.value = null
}

async function fetchUsers() {
  try {
    allUsers.value = await api<any[]>('/api/users/')
  } catch (e) {
    console.error('Failed to load users:', e)
  }
}

async function linkAuthor(aliasId: number, userId: number | null) {
  try {
    await api(`/api/repos/${route.params.id}/git-author-aliases/${aliasId}/`, {
      method: 'PATCH',
      body: { user: userId },
    })
    toast.add({ title: '关联成功', color: 'success' })
    await fetchInsights()
  } catch (e) {
    toast.add({ title: '关联失败', color: 'error' })
  }
}
```

- [ ] **Step 3: Add watch for insights tab and days filter**

Add after the existing `watch(activeTab, ...)`:

```typescript
watch(activeTab, (val) => {
  if (val === 'insights' && repo.value?.clone_status === 'cloned' && !insightsData.value) {
    fetchInsights()
  }
})

watch(insightsDays, () => {
  if (activeTab.value === 'insights') {
    fetchInsights()
    if (selectedDeveloper.value) {
      fetchDeveloperDetail(selectedDeveloper.value.alias_id)
    }
  }
})
```

- [ ] **Step 4: Add the insights tab template**

Add after the `</template>` of `#git-log` slot (before `</UTabs>`):

```html
      <template #insights>
        <div class="mt-4">
          <!-- Loading -->
          <div v-if="insightsLoading" class="flex items-center justify-center py-10">
            <div class="text-sm text-gray-400 dark:text-gray-500">加载开发者洞察中...</div>
          </div>
          <!-- Not Cloned -->
          <div v-else-if="repo.clone_status !== 'cloned'" class="flex items-center justify-center py-10">
            <div class="text-sm text-gray-400 dark:text-gray-500">请先同步代码后查看开发者洞察</div>
          </div>
          <!-- Individual Detail View -->
          <div v-else-if="selectedDeveloper && developerDetail" class="space-y-4">
            <div class="flex items-center justify-between">
              <button class="text-sm text-primary hover:underline" @click="backToTeam">← 返回团队总览</button>
              <USelect v-model="insightsDays" :items="daysOptions" value-key="value" size="xs" />
            </div>
            <!-- Header -->
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                <span class="text-primary font-semibold">{{ developerDetail.author_name?.slice(0, 1)?.toUpperCase() }}</span>
              </div>
              <div>
                <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ developerDetail.author_name }}</h3>
                <p class="text-xs text-gray-400 dark:text-gray-500">{{ developerDetail.author_email }}<span v-if="developerDetail.user_name"> · {{ developerDetail.user_name }}</span></p>
              </div>
            </div>
            <!-- Radar Chart -->
            <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4">
              <ChartsRadarChart
                :indicators="[
                  { name: '贡献量', max: 100 },
                  { name: '效率', max: 100 },
                  { name: '能力', max: 100 },
                  { name: '质量', max: 100 },
                ]"
                :values="[
                  developerDetail.scores.contribution,
                  developerDetail.scores.efficiency,
                  developerDetail.scores.capability,
                  developerDetail.scores.quality,
                ]"
                :height="280"
              />
            </div>
            <!-- Detail Cards -->
            <div class="grid grid-cols-2 gap-3">
              <div class="bg-emerald-50 dark:bg-emerald-950/30 rounded-xl p-4">
                <p class="text-xs font-semibold text-emerald-600 dark:text-emerald-400 mb-2">贡献量</p>
                <p class="text-sm text-gray-700 dark:text-gray-300">提交数: {{ developerDetail.details.commit_count }}</p>
                <p class="text-sm text-gray-700 dark:text-gray-300">代码行数: +{{ developerDetail.details.additions }} / -{{ developerDetail.details.deletions }}</p>
              </div>
              <div class="bg-blue-50 dark:bg-blue-950/30 rounded-xl p-4">
                <p class="text-xs font-semibold text-blue-600 dark:text-blue-400 mb-2">效率</p>
                <p class="text-sm text-gray-700 dark:text-gray-300">频率: {{ developerDetail.details.commit_frequency }}/周</p>
                <p class="text-sm text-gray-700 dark:text-gray-300">活跃天数: {{ developerDetail.details.active_days_ratio }}%</p>
              </div>
              <div class="bg-amber-50 dark:bg-amber-950/30 rounded-xl p-4">
                <p class="text-xs font-semibold text-amber-600 dark:text-amber-400 mb-2">能力</p>
                <p class="text-sm text-gray-700 dark:text-gray-300">涉及目录: {{ developerDetail.details.directory_count }} 个</p>
                <p class="text-sm text-gray-700 dark:text-gray-300">
                  类型:
                  <span v-for="(count, type) in developerDetail.details.commit_types" :key="type" class="mr-1">
                    {{ type }} {{ count }}
                  </span>
                </p>
              </div>
              <div class="bg-purple-50 dark:bg-purple-950/30 rounded-xl p-4">
                <p class="text-xs font-semibold text-purple-600 dark:text-purple-400 mb-2">质量</p>
                <p class="text-sm text-gray-700 dark:text-gray-300">Fix 占比: {{ developerDetail.details.fix_ratio }}%</p>
                <p class="text-sm text-gray-700 dark:text-gray-300">规范度: {{ developerDetail.details.conventional_ratio }}%</p>
              </div>
            </div>
            <!-- AI Placeholder -->
            <div class="border border-dashed border-gray-200 dark:border-gray-700 rounded-xl p-4">
              <p class="text-xs font-semibold text-gray-400 dark:text-gray-500">🤖 AI 洞察 (即将推出)</p>
              <p class="text-xs text-gray-300 dark:text-gray-600 mt-1 italic">基于提交历史和 Issue 数据的综合分析...</p>
            </div>
          </div>
          <!-- Loading Detail -->
          <div v-else-if="selectedDeveloper && developerDetailLoading" class="flex items-center justify-center py-10">
            <div class="text-sm text-gray-400 dark:text-gray-500">加载开发者详情中...</div>
          </div>
          <!-- Team Overview -->
          <div v-else-if="insightsData" class="space-y-4">
            <!-- Time filter -->
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">开发者洞察</span>
              <USelect v-model="insightsDays" :items="daysOptions" value-key="value" size="xs" />
            </div>
            <!-- Unlinked authors alert -->
            <UAlert
              v-if="insightsData.unlinked_count > 0"
              color="warning"
              variant="subtle"
              icon="i-heroicons-exclamation-triangle"
              :title="`${insightsData.unlinked_count} 位作者未关联用户`"
              :actions="[{ label: '去关联', click: () => { showLinkModal = true; fetchUsers() } }]"
            />
            <!-- Developer Cards -->
            <div class="space-y-3">
              <div
                v-for="dev in insightsData.developers"
                :key="dev.author_email"
                class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4 cursor-pointer hover:border-primary transition-colors"
                @click="selectDeveloper(dev)"
              >
                <div class="flex items-center justify-between mb-3">
                  <div class="flex items-center gap-2">
                    <div class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                      <span class="text-primary text-sm font-semibold">{{ dev.author_name?.slice(0, 1)?.toUpperCase() }}</span>
                    </div>
                    <div>
                      <span class="text-sm font-medium text-gray-900 dark:text-gray-100">{{ dev.author_name }}</span>
                      <span class="text-xs text-gray-400 dark:text-gray-500 ml-2">{{ dev.stats.commit_count }} commits</span>
                      <span v-if="dev.user_name" class="text-xs text-gray-400 dark:text-gray-500 ml-1">· {{ dev.user_name }}</span>
                    </div>
                  </div>
                  <span class="text-xs text-primary">查看详情 →</span>
                </div>
                <!-- Score bars -->
                <div class="grid grid-cols-4 gap-3">
                  <div v-for="(dim, key) in { contribution: '贡献量', efficiency: '效率', capability: '能力', quality: '质量' }" :key="key">
                    <div class="flex justify-between text-[11px] mb-1">
                      <span class="text-gray-500 dark:text-gray-400">{{ dim }}</span>
                      <span class="font-semibold" :class="scoreColor(key as string)">{{ dev.scores[key] }}</span>
                    </div>
                    <div class="h-1 bg-gray-100 dark:bg-gray-800 rounded-full">
                      <div class="h-full rounded-full transition-all" :class="scoreBarColor(key as string)" :style="{ width: dev.scores[key] + '%' }" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Link Authors Modal -->
          <USlideover v-model:open="showLinkModal" title="关联 Git 作者" side="right">
            <template #content>
              <div class="p-6 space-y-4">
                <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">关联 Git 作者到系统用户</h3>
                <div v-for="author in insightsData?.unlinked_authors" :key="author.id" class="flex items-center gap-3 py-2 border-b border-gray-100 dark:border-gray-800">
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{{ author.author_name }}</p>
                    <p class="text-xs text-gray-400 dark:text-gray-500 truncate">{{ author.author_email }}</p>
                  </div>
                  <USelect
                    :items="allUsers.map(u => ({ label: u.name || u.username, value: u.id }))"
                    value-key="value"
                    placeholder="选择用户"
                    size="sm"
                    class="w-40"
                    @update:model-value="(val: any) => linkAuthor(author.id, val)"
                  />
                </div>
              </div>
            </template>
          </USlideover>
        </div>
      </template>
```

- [ ] **Step 5: Add score color helper functions**

Add to `<script setup>`:

```typescript
function scoreColor(key: string): string {
  const colors: Record<string, string> = {
    contribution: 'text-emerald-600 dark:text-emerald-400',
    efficiency: 'text-blue-600 dark:text-blue-400',
    capability: 'text-amber-600 dark:text-amber-400',
    quality: 'text-purple-600 dark:text-purple-400',
  }
  return colors[key] || ''
}

function scoreBarColor(key: string): string {
  const colors: Record<string, string> = {
    contribution: 'bg-emerald-500',
    efficiency: 'bg-blue-500',
    capability: 'bg-amber-500',
    quality: 'bg-purple-500',
  }
  return colors[key] || ''
}
```

- [ ] **Step 6: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 7: Commit**

```bash
cd frontend
git add app/pages/app/repos/[id]/index.vue
git commit -m "feat(frontend): add developer insights tab with team overview and individual detail"
```

---

### Task 8: Integration Testing and Polish

**Files:**
- Various backend test files

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && uv run pytest -v`
Expected: All tests PASS

- [ ] **Step 2: Run frontend typecheck**

Run: `cd frontend && npx nuxi typecheck`
Expected: No type errors (or only pre-existing ones)

- [ ] **Step 3: Manual verification checklist**

Verify via browser at `http://localhost:3004/app/repos/{id}`:

1. Third tab "开发者洞察" appears
2. Clicking tab loads developer cards with score bars
3. Time filter (30天/90天/全部) works
4. Clicking a developer shows radar chart + detail cards
5. "← 返回团队总览" button works
6. Unlinked authors alert shows (if applicable)
7. Link modal opens and user selection works
8. Dark mode renders correctly

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat(repos): developer insights — four-dimension capability assessment

Adds Commit persistence, GitAuthorAlias mapping, DeveloperInsightsService
with percentile-based scoring (contribution/efficiency/capability/quality),
API endpoints, and frontend tab with team overview + individual radar chart."
```
