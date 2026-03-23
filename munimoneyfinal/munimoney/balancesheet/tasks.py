"""
Celery tasks for the balancesheet app.

Defines scheduled tasks for the automated data pipeline:
- Monthly full pipeline run (1st of each month at 02:00 UTC)
- Weekly data validation check (every Monday at 06:00 UTC)

To register the beat schedule, add CELERY_BEAT_SCHEDULE to settings.py
or use the schedule defined here via ``app.conf.beat_schedule``.
"""

import logging
from datetime import datetime

from celery import shared_task
from celery.schedules import crontab
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="balancesheet.tasks.run_full_pipeline",
    max_retries=1,
    default_retry_delay=600,
    acks_late=True,
)
def run_full_pipeline(self):
    """
    Execute the full data pipeline as a Celery task.

    Scheduled to run on the 1st of each month at 02:00 UTC.
    Calls the ``run_pipeline`` management command which orchestrates
    pull_data -> engineer_features -> retrain_models.
    """
    logger.info("Celery task run_full_pipeline started at %s", datetime.utcnow())
    try:
        call_command("run_pipeline")
        logger.info("Celery task run_full_pipeline completed successfully.")
        return {"status": "success", "timestamp": str(datetime.utcnow())}
    except Exception as exc:
        logger.error("Celery task run_full_pipeline failed: %s", exc)
        # Retry once after 10 minutes
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="balancesheet.tasks.weekly_data_validation",
    max_retries=1,
    default_retry_delay=300,
    acks_late=True,
)
def weekly_data_validation(self):
    """
    Run a weekly data validation check.

    Scheduled to run every Monday at 06:00 UTC.
    Performs a dry-run data pull and feature engineering to detect
    issues before the monthly retrain.
    """
    logger.info("Celery task weekly_data_validation started at %s", datetime.utcnow())
    issues = []

    # Check 1: Verify API is reachable with a dry-run pull
    try:
        call_command("pull_data", "--dry-run")
        logger.info("Data pull dry-run: OK")
    except Exception as exc:
        msg = f"Data pull dry-run failed: {exc}"
        logger.warning(msg)
        issues.append(msg)

    # Check 2: Verify feature engineering can run
    try:
        call_command("engineer_features")
        logger.info("Feature engineering: OK")
    except Exception as exc:
        msg = f"Feature engineering check failed: {exc}"
        logger.warning(msg)
        issues.append(msg)

    # Check 3: Verify database has recent data
    try:
        from balancesheet.models import BalSheet
        total_records = BalSheet.objects.count()
        if total_records == 0:
            issues.append("BalSheet table is empty.")
        else:
            logger.info("BalSheet records: %d", total_records)
    except Exception as exc:
        issues.append(f"Database check failed: {exc}")

    result = {
        "status": "healthy" if not issues else "issues_found",
        "issues": issues,
        "timestamp": str(datetime.utcnow()),
    }
    logger.info("Weekly validation result: %s", result)
    return result


# ---------------------------------------------------------------
# Beat schedule configuration
# ---------------------------------------------------------------
# This can be imported into celery.py or settings.py to register
# the periodic tasks with Celery Beat.

CELERY_BEAT_SCHEDULE = {
    "monthly-full-pipeline": {
        "task": "balancesheet.tasks.run_full_pipeline",
        "schedule": crontab(day_of_month="1", hour="2", minute="0"),
        "options": {"queue": "pipeline"},
    },
    "weekly-data-validation": {
        "task": "balancesheet.tasks.weekly_data_validation",
        "schedule": crontab(day_of_week="monday", hour="6", minute="0"),
        "options": {"queue": "pipeline"},
    },
}
