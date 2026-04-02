from django.apps import AppConfig


class AiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai"
    verbose_name = "AI 分析"

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(self._cleanup_stale, sender=self)

    @staticmethod
    def _cleanup_stale(**kwargs):
        from .services import IssueAnalysisService
        try:
            IssueAnalysisService.cleanup_stale_analyses()
        except Exception:
            pass
