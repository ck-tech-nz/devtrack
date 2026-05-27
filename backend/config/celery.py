import os
from pathlib import Path
from celery import Celery

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("devtrack")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
