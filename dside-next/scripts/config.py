"""
Configuration module for DSIDE data ingestion scripts.

Loads environment variables, initializes the Supabase client,
and defines constants for all external API endpoints.
"""

import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
SEED_DIR = DATA_DIR / "seed"
RAW_DIR = DATA_DIR / "raw"
STATSSA_DIR = DATA_DIR / "statssa"
LOG_DIR = PROJECT_ROOT / "logs"

# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
ENV_PATH = PROJECT_ROOT / ".env.local"
load_dotenv(dotenv_path=ENV_PATH)

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Optional overrides — fall back to well-known public endpoints
MUNICIPAL_MONEY_API: str = os.getenv(
    "MUNICIPAL_MONEY_API",
    "https://municipaldata.treasury.gov.za/api",
)
VULEKAMALI_API: str = os.getenv(
    "VULEKAMALI_API",
    "https://vulekamali.gov.za/api",
)

# ---------------------------------------------------------------------------
# Supabase client (lazy — only created when credentials are present)
# ---------------------------------------------------------------------------
_supabase_client: Client | None = None


def get_supabase() -> Client:
    """Return a cached Supabase client, creating it on first call."""
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in "
                f"{ENV_PATH} (or as environment variables)."
            )
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _supabase_client


# ---------------------------------------------------------------------------
# API endpoint constants
# ---------------------------------------------------------------------------

# Municipal Money (National Treasury municipal data)
MM_FINANCIAL_POSITION = f"{MUNICIPAL_MONEY_API}/cubes/financial_position/facts"
MM_INCOME_EXPENDITURE = f"{MUNICIPAL_MONEY_API}/cubes/incexp/facts"
MM_CAPITAL = f"{MUNICIPAL_MONEY_API}/cubes/capital/facts"
MM_AGED_CREDITOR = f"{MUNICIPAL_MONEY_API}/cubes/aged_creditor/facts"
MM_AUDIT_OPINIONS = f"{MUNICIPAL_MONEY_API}/cubes/audit_opinions/facts"
MM_MUNICIPALITIES = f"{MUNICIPAL_MONEY_API}/cubes/municipalities/members"

# Vulekamali (National & Provincial budgets)
VK_PROVINCIAL_EXPENDITURE = f"{VULEKAMALI_API}/v2/provincial-expenditure/"
VK_NATIONAL_EXPENDITURE = f"{VULEKAMALI_API}/v2/national-expenditure/"

# StatsSA (Quarterly Labour Force Survey publications page)
STATSSA_QLFS_BASE = "https://www.statssa.gov.za/publications/P0211/"

# Wazimap / Youth Explorer
WAZIMAP_API = "https://wazimap.co.za/api/v1"
WAZIMAP_PROFILE = f"{WAZIMAP_API}/profiles/{{geo_code}}/"

# ---------------------------------------------------------------------------
# Pagination defaults
# ---------------------------------------------------------------------------
DEFAULT_PAGE_SIZE = 1000
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds — multiplied by attempt number
REQUEST_TIMEOUT = 60  # seconds

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(name: str = "dside_ingestion", level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger that writes to console and log file."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        # Console handler
        console = logging.StreamHandler()
        console.setLevel(level)
        console.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
        logger.addHandler(console)

        # File handler
        log_file = LOG_DIR / "ingestion.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
        logger.addHandler(file_handler)

    return logger
