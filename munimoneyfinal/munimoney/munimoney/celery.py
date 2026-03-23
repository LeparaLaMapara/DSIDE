"""
Celery configuration for the Municipal Money Django project.

This module sets up Celery with Django settings and enables
auto-discovery of tasks across all installed apps.

To start the worker:
    celery -A munimoney worker --loglevel=info

To start the beat scheduler:
    celery -A munimoney beat --loglevel=info
"""

import os

from celery import Celery

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "munimoney.settings")

app = Celery("munimoney")

# Load configuration from Django settings, using the CELERY_ namespace
# so that all Celery-related settings must be prefixed with CELERY_.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in all installed Django apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task that prints its own request info."""
    print(f"Request: {self.request!r}")
