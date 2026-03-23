"""
Management command to orchestrate the full data pipeline:
pull_data -> engineer_features -> retrain_models.

Usage:
    python manage.py run_pipeline
    python manage.py run_pipeline --notify
    python manage.py run_pipeline --skip-pull
"""

import logging
import sys
import time
from datetime import datetime

from django.core.management import call_command
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

# Exit codes
EXIT_SUCCESS = 0
EXIT_DATA_PULL_FAILED = 1
EXIT_FEATURE_ENGINEERING_FAILED = 2
EXIT_RETRAIN_FAILED = 3


class Command(BaseCommand):
    """Run the full municipal data pipeline end-to-end."""

    help = (
        "Orchestrate the full pipeline: pull data, engineer features, "
        "and retrain models."
    )

    def add_arguments(self, parser):
        """Define command-line arguments."""
        parser.add_argument(
            "--notify",
            action="store_true",
            default=False,
            help="Send a summary notification when complete (future: email/Slack).",
        )
        parser.add_argument(
            "--skip-pull",
            action="store_true",
            default=False,
            help="Skip the data pull step (use existing data).",
        )
        parser.add_argument(
            "--skip-features",
            action="store_true",
            default=False,
            help="Skip the feature engineering step (use existing features).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Pass --dry-run to the data pull step.",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=None,
            help="Financial year to pass to pull_data.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Force model replacement (skip quality gate).",
        )

    def handle(self, *args, **options):
        """Execute the full pipeline."""
        start_time = time.time()
        run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        summary = {
            "started_at": run_timestamp,
            "steps": {},
        }

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n{'='*60}\n  Municipal Money Pipeline\n  Started: {run_timestamp}\n{'='*60}\n"
        ))

        # -------------------------------------------------------
        # Step 1: Pull Data
        # -------------------------------------------------------
        if not options["skip_pull"]:
            self.stdout.write(self.style.MIGRATE_HEADING("\n[1/3] Pulling data..."))
            try:
                pull_args = []
                if options["dry_run"]:
                    pull_args.append("--dry-run")
                if options["year"]:
                    pull_args.extend(["--year", str(options["year"])])

                call_command("pull_data", *pull_args, stdout=self.stdout, stderr=self.stderr)
                summary["steps"]["pull_data"] = "SUCCESS"
            except Exception as exc:
                logger.error("Data pull failed: %s", exc)
                summary["steps"]["pull_data"] = f"FAILED: {exc}"
                self.stdout.write(self.style.ERROR(f"Data pull failed: {exc}"))
                self._send_notification(options["notify"], summary)
                sys.exit(EXIT_DATA_PULL_FAILED)
        else:
            self.stdout.write("[1/3] Skipping data pull (--skip-pull).")
            summary["steps"]["pull_data"] = "SKIPPED"

        # -------------------------------------------------------
        # Step 2: Engineer Features
        # -------------------------------------------------------
        if not options["skip_features"]:
            self.stdout.write(self.style.MIGRATE_HEADING("\n[2/3] Engineering features..."))
            try:
                call_command("engineer_features", stdout=self.stdout, stderr=self.stderr)
                summary["steps"]["engineer_features"] = "SUCCESS"
            except Exception as exc:
                logger.error("Feature engineering failed: %s", exc)
                summary["steps"]["engineer_features"] = f"FAILED: {exc}"
                self.stdout.write(self.style.ERROR(f"Feature engineering failed: {exc}"))
                self._send_notification(options["notify"], summary)
                sys.exit(EXIT_FEATURE_ENGINEERING_FAILED)
        else:
            self.stdout.write("[2/3] Skipping feature engineering (--skip-features).")
            summary["steps"]["engineer_features"] = "SKIPPED"

        # -------------------------------------------------------
        # Step 3: Retrain Models
        # -------------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("\n[3/3] Retraining models..."))
        try:
            retrain_args = []
            if options["force"]:
                retrain_args.append("--force")

            call_command("retrain_models", *retrain_args, stdout=self.stdout, stderr=self.stderr)
            summary["steps"]["retrain_models"] = "SUCCESS"
        except Exception as exc:
            logger.error("Model retraining failed: %s", exc)
            summary["steps"]["retrain_models"] = f"FAILED: {exc}"
            self.stdout.write(self.style.ERROR(f"Model retraining failed: {exc}"))
            self._send_notification(options["notify"], summary)
            sys.exit(EXIT_RETRAIN_FAILED)

        # -------------------------------------------------------
        # Summary
        # -------------------------------------------------------
        elapsed = time.time() - start_time
        summary["elapsed_seconds"] = round(elapsed, 1)
        summary["status"] = "SUCCESS"

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n{'='*60}\n  Pipeline Complete\n{'='*60}"
        ))
        self.stdout.write(f"  Duration: {elapsed:.1f}s")
        for step, status in summary["steps"].items():
            self.stdout.write(f"  {step}: {status}")
        self.stdout.write("")

        self._send_notification(options["notify"], summary)
        logger.info("Pipeline complete in %.1f seconds. Summary: %s", elapsed, summary)

    def _send_notification(self, should_notify, summary):
        """
        Send a pipeline summary notification.

        Currently logs a placeholder. Future integration point for
        email, Slack, or other notification services.
        """
        if not should_notify:
            return

        # Future: integrate with Django email, Slack webhook, etc.
        logger.info("NOTIFICATION (placeholder): Pipeline summary: %s", summary)
        self.stdout.write(
            self.style.WARNING(
                "  --notify flag set but notification service not yet configured. "
                "Summary logged."
            )
        )
