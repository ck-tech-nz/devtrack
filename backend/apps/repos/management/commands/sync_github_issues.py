from django.core.management.base import BaseCommand, CommandError
from apps.repos.services import GitHubSyncService
from apps.repos.models import Repo


class Command(BaseCommand):
    help = "Sync GitHub issues for configured repositories"

    def add_arguments(self, parser):
        parser.add_argument("--repo", type=str, help="Repo full_name, e.g. org/name")

    def handle(self, *args, **options):
        service = GitHubSyncService()
        if options["repo"]:
            try:
                repo = Repo.objects.get(full_name=options["repo"])
            except Repo.DoesNotExist:
                raise CommandError(f"Repo '{options['repo']}' not found")
            service.sync_repo(repo)
            self.stdout.write(self.style.SUCCESS(f"Synced {repo.full_name}"))
        else:
            service.sync_all()
            self.stdout.write(self.style.SUCCESS("Synced all repos"))
