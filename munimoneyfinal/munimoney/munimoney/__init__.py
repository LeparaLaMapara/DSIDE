"""
Municipal Money Django project package.

This module ensures the Celery app is loaded when Django starts,
so that the ``@shared_task`` decorator uses the correct app instance.
"""

try:
    from .celery import app as celery_app
    __all__ = ("celery_app",)
except ImportError:
    # Celery not installed — pipeline tasks won't run but Django works fine
    celery_app = None
    __all__ = ()
