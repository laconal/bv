import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "birid.settings")

app = Celery("birid")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "sweep-stuck-photo-processing": {
        "task": "products.tasks.sweep_stuck_photo_processing",
        "schedule": 600.0,  # every 10 minutes - cheap indexed query, see _STUCK_THRESHOLD in products/tasks.py
    },
    "sweep-stuck-avatar-processing": {
        "task": "buyers.tasks.sweep_stuck_avatar_processing",
        "schedule": 600.0,  # every 10 minutes - cheap indexed query, see _STUCK_THRESHOLD in buyers/tasks.py
    },
}
