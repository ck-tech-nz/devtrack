from django.apps import AppConfig


class AiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai"
    verbose_name = "AI 分析"

    def ready(self):
        from .services import IssueAnalysisService
        try:
            IssueAnalysisService.cleanup_stale_analyses()
        except Exception:
            pass  # DB may not be ready during initial migration
