"""
DSIDE ML Pipeline Orchestrator.

Runs the full ML pipeline in order:
    1. PCA Analysis
    2. Train SVM
    3. Train Random Forest
    4. Compute Skills Gap

Usage:
    python -m scripts.ml.run_ml_pipeline
    python -m scripts.ml.run_ml_pipeline --step pca
    python -m scripts.ml.run_ml_pipeline --step svm --force
    python -m scripts.ml.run_ml_pipeline --force
    python scripts/ml/run_ml_pipeline.py
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ml_pipeline")

VALID_STEPS = ["pca", "svm", "rf", "skills_gap"]


def run_pca() -> bool:
    """Run PCA analysis step."""
    from scripts.ml.pca_analysis import main as pca_main

    try:
        pca_main()
        return True
    except Exception as exc:
        logger.error("PCA analysis failed: %s", exc, exc_info=True)
        return False


def run_svm(force: bool = False) -> bool:
    """Run SVM training step."""
    from scripts.ml.train_svm import load_training_data, train_svm

    try:
        X, y, feature_names = load_training_data()
        train_svm(X, y, feature_names, force=force)
        return True
    except Exception as exc:
        logger.error("SVM training failed: %s", exc, exc_info=True)
        return False


def run_rf(force: bool = False) -> bool:
    """Run Random Forest training step."""
    from scripts.ml.train_rf import load_training_data, train_rf

    try:
        X, y, feature_names = load_training_data()
        train_rf(X, y, feature_names, force=force)
        return True
    except Exception as exc:
        logger.error("RF training failed: %s", exc, exc_info=True)
        return False


def run_skills_gap() -> bool:
    """Run skills gap analysis step."""
    from scripts.ml.compute_skills_gap import main as skills_main

    try:
        skills_main()
        return True
    except Exception as exc:
        logger.error("Skills gap analysis failed: %s", exc, exc_info=True)
        return False


STEP_RUNNERS = {
    "pca": run_pca,
    "svm": run_svm,
    "rf": run_rf,
    "skills_gap": run_skills_gap,
}

STEP_NAMES = {
    "pca": "PCA Analysis",
    "svm": "SVM Municipality Profiling",
    "rf": "Random Forest Employment Prediction",
    "skills_gap": "Skills Gap Analysis",
}


def main() -> None:
    """Run the ML pipeline orchestrator."""
    parser = argparse.ArgumentParser(description="DSIDE ML Pipeline Orchestrator")
    parser.add_argument(
        "--step",
        type=str,
        choices=VALID_STEPS,
        default=None,
        help="Run a specific step only. Options: pca, svm, rf, skills_gap",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip quality gates for model training steps.",
    )
    args = parser.parse_args()

    start_time = time.time()
    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    steps_to_run = [args.step] if args.step else VALID_STEPS

    print("\n" + "=" * 60)
    print("  DSIDE ML Pipeline")
    print(f"  Started: {run_timestamp}")
    print(f"  Steps:   {', '.join(steps_to_run)}")
    print(f"  Force:   {args.force}")
    print("=" * 60 + "\n")

    results = {}

    for i, step in enumerate(steps_to_run, 1):
        step_name = STEP_NAMES.get(step, step)
        total = len(steps_to_run)

        print(f"\n[{i}/{total}] {step_name}")
        print("-" * 50)

        step_start = time.time()

        runner = STEP_RUNNERS[step]
        # Pass force flag to training steps
        if step in ("svm", "rf"):
            success = runner(force=args.force)
        else:
            success = runner()

        step_elapsed = time.time() - step_start
        status = "SUCCESS" if success else "FAILED"
        results[step] = {
            "status": status,
            "elapsed": round(step_elapsed, 1),
        }

        logger.info(
            "Step %s: %s (%.1fs)", step_name, status, step_elapsed
        )

        if not success and not args.force:
            logger.error("Pipeline halted due to failure in %s", step_name)
            print(f"\nPipeline HALTED: {step_name} failed.")
            break

    # Summary
    total_elapsed = time.time() - start_time
    all_success = all(r["status"] == "SUCCESS" for r in results.values())

    print("\n" + "=" * 60)
    print("  Pipeline Summary")
    print("=" * 60)
    print(f"  Status:   {'SUCCESS' if all_success else 'FAILED'}")
    print(f"  Duration: {total_elapsed:.1f}s")
    print()
    for step, result in results.items():
        step_name = STEP_NAMES.get(step, step)
        icon = "[OK]" if result["status"] == "SUCCESS" else "[!!]"
        print(f"  {icon} {step_name}: {result['status']} ({result['elapsed']}s)")
    print("=" * 60 + "\n")

    if not all_success:
        sys.exit(1)


if __name__ == "__main__":
    main()
