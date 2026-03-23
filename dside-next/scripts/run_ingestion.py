#!/usr/bin/env python3
"""
Orchestrator for all DSIDE data ingestion pipelines.

Usage examples
--------------
    # Run everything
    python run_ingestion.py --all

    # Seed data only (no API calls)
    python run_ingestion.py --seed-only

    # Specific source
    python run_ingestion.py --source municipal_money

    # Dry run (fetch + clean but don't write)
    python run_ingestion.py --all --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time

from config import setup_logging

logger = setup_logging("run_ingestion")

# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------

SOURCES = {
    "municipal_money": {
        "module": "ingest_municipal_money",
        "description": "Municipal Money API (National Treasury)",
        "is_seed": False,
    },
    "vulekamali": {
        "module": "ingest_vulekamali",
        "description": "Vulekamali national & provincial budgets",
        "is_seed": False,
    },
    "statssa": {
        "module": "ingest_statssa",
        "description": "StatsSA Quarterly Labour Force Survey",
        "is_seed": False,
    },
    "youth_explorer": {
        "module": "ingest_youth_explorer",
        "description": "Wazimap / Youth Explorer demographic profiles",
        "is_seed": False,
    },
    "skills": {
        "module": "ingest_skills",
        "description": "Scarce skills & training programs (seed data)",
        "is_seed": True,
    },
    "opportunities": {
        "module": "ingest_opportunities",
        "description": "Youth opportunities (seed + scrapers)",
        "is_seed": True,
    },
}

# Execution order — seed data first, then API sources
EXECUTION_ORDER = [
    "skills",
    "opportunities",
    "municipal_money",
    "vulekamali",
    "statssa",
    "youth_explorer",
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_source(name: str, dry_run: bool = False, seed_only: bool = False) -> dict:
    """Import and execute a single ingestion source."""
    import importlib

    info = SOURCES[name]
    module = importlib.import_module(info["module"])

    logger.info("=" * 60)
    logger.info("STARTING: %s — %s", name, info["description"])
    logger.info("=" * 60)

    start = time.time()
    try:
        # Each module exposes a run() function
        kwargs: dict = {"dry_run": dry_run}

        # Pass seed_only to opportunities module
        if name == "opportunities" and seed_only:
            kwargs["seed_only"] = True

        result = module.run(**kwargs)
        elapsed = time.time() - start

        logger.info("COMPLETED: %s in %.1fs", name, elapsed)
        return {"status": "ok", "elapsed": elapsed, "rows": result}

    except Exception as exc:
        elapsed = time.time() - start
        logger.exception("FAILED: %s after %.1fs", name, elapsed)
        return {"status": "error", "elapsed": elapsed, "error": str(exc), "rows": {}}


def run_all(
    sources: list[str] | None = None,
    dry_run: bool = False,
    seed_only: bool = False,
) -> dict:
    """Run multiple ingestion sources and produce a summary report."""
    if sources:
        order = [s for s in EXECUTION_ORDER if s in sources]
        # Add any requested sources not in the default order
        for s in sources:
            if s not in order:
                order.append(s)
    elif seed_only:
        order = [s for s in EXECUTION_ORDER if SOURCES[s]["is_seed"]]
    else:
        order = list(EXECUTION_ORDER)

    total_start = time.time()
    results: dict[str, dict] = {}

    for name in order:
        if name not in SOURCES:
            logger.error("Unknown source: %s (available: %s)", name, ", ".join(SOURCES))
            continue
        results[name] = run_source(name, dry_run=dry_run, seed_only=seed_only)

    total_elapsed = time.time() - total_start

    # Summary report
    logger.info("")
    logger.info("=" * 60)
    logger.info("INGESTION SUMMARY")
    logger.info("=" * 60)
    logger.info("Total elapsed: %.1fs", total_elapsed)
    logger.info("")

    total_rows = 0
    errors = 0
    for name, res in results.items():
        status_icon = "OK" if res["status"] == "ok" else "FAIL"
        row_summary = res.get("rows", {})
        row_count = sum(v for v in row_summary.values() if isinstance(v, int))
        total_rows += row_count

        logger.info(
            "  [%4s] %-20s  %5d rows  %.1fs",
            status_icon, name, row_count, res["elapsed"],
        )
        if res["status"] == "error":
            errors += 1
            logger.info("         Error: %s", res.get("error", "unknown"))

    logger.info("")
    logger.info("Total rows processed: %d", total_rows)
    logger.info("Sources succeeded: %d / %d", len(results) - errors, len(results))
    if errors:
        logger.warning("%d source(s) had errors — see log for details", errors)
    logger.info("=" * 60)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="DSIDE data ingestion orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Available sources: {', '.join(SOURCES.keys())}",
    )
    parser.add_argument(
        "--source", type=str, nargs="+",
        help="Run specific source(s) only",
    )
    parser.add_argument("--all", action="store_true", help="Run all sources")
    parser.add_argument("--seed-only", action="store_true", help="Only run seed data sources")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and process but do not write to Supabase")
    parser.add_argument("--list", action="store_true", help="List available sources and exit")
    args = parser.parse_args()

    if args.list:
        print("Available ingestion sources:")
        for name, info in SOURCES.items():
            seed_tag = " [SEED]" if info["is_seed"] else ""
            print(f"  {name:<20s} {info['description']}{seed_tag}")
        sys.exit(0)

    if not args.all and not args.source and not args.seed_only:
        parser.print_help()
        print("\nError: specify --all, --seed-only, or --source <name>")
        sys.exit(1)

    # Validate source names
    if args.source:
        for s in args.source:
            if s not in SOURCES:
                print(f"Error: unknown source '{s}'. Available: {', '.join(SOURCES.keys())}")
                sys.exit(1)

    run_all(
        sources=args.source,
        dry_run=args.dry_run,
        seed_only=args.seed_only,
    )


if __name__ == "__main__":
    main()
