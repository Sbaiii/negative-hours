"""Shared configuration for the extraction pipeline."""

from pathlib import Path

# Bidding zones in scope (see control-room ADR-002). Keys are entsoe-py area codes.
ZONES: dict[str, str] = {
    "ES": "Spain",
    "PT": "Portugal",
    "FR": "France",
    "DE_LU": "Germany-Luxembourg",
    "NL": "Netherlands",
    "BE": "Belgium",
    "PL": "Poland",
    "IT_NORD": "North Italy",
}

DEFAULT_START_YEAR = 2019

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_PRICES_DIR = REPO_ROOT / "data" / "raw" / "prices"

# Retry policy for ENTSO-E API calls: wait 5s, 10s, 20s, 40s between attempts.
MAX_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 5
REQUEST_TIMEOUT_SECONDS = 60
