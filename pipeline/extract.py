"""Pull ENTSO-E data and save it as Parquet, one file per dataset, zone and year.

Datasets (folder under data/raw/ → columns):
    prices      ts_utc, zone, price_eur_mwh, resolution_minutes
    generation  ts_utc, zone, production_type, generation_mw, resolution_minutes
    load        ts_utc, zone, load_mw, resolution_minutes

Output: data/raw/<dataset>/zone=<ZONE>/year=<YYYY>.parquet

Years are UTC calendar years. The current year is always re-downloaded because it is
still filling up; past years are skipped if their file exists (use --force to redo them).

Usage:
    uv run python -m pipeline.extract
    uv run python -m pipeline.extract --datasets prices --zones ES DE_LU --start-year 2023
"""

import argparse
import logging
import sys

import pandas as pd
import requests
from entsoe import EntsoePandasClient

from pipeline.common import (
    Dataset,
    RedactingFormatter,
    extract_zone_year,
    get_api_key,
)
from pipeline.config import DEFAULT_START_YEAR, REQUEST_TIMEOUT_SECONDS, ZONES
from pipeline.generation import GENERATION
from pipeline.load import LOAD
from pipeline.prices import PRICES

log = logging.getLogger("extract")

DATASETS: dict[str, Dataset] = {d.name: d for d in (PRICES, GENERATION, LOAD)}


def parse_args() -> argparse.Namespace:
    current_year = pd.Timestamp.now(tz="UTC").year
    parser = argparse.ArgumentParser(
        description="Download ENTSO-E prices, generation and load to Parquet."
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=list(DATASETS),
        choices=list(DATASETS),
        metavar="DATASET",
        help=f"Datasets to pull (default: all). Choices: {' '.join(DATASETS)}",
    )
    parser.add_argument(
        "--zones",
        nargs="+",
        default=list(ZONES),
        choices=list(ZONES),
        metavar="ZONE",
        help=f"Bidding zones to pull (default: all). Choices: {' '.join(ZONES)}",
    )
    parser.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR)
    parser.add_argument("--end-year", type=int, default=current_year)
    parser.add_argument(
        "--force", action="store_true", help="Overwrite files that already exist."
    )
    args = parser.parse_args()
    if args.start_year > args.end_year:
        parser.error("--start-year must be <= --end-year")
    if args.end_year > current_year:
        parser.error(
            f"--end-year cannot be in the future (current year is {current_year})"
        )
    return args


def main() -> int:
    handler = logging.StreamHandler()
    handler.setFormatter(
        RedactingFormatter(
            "%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S"
        )
    )
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    args = parse_args()
    client = EntsoePandasClient(api_key=get_api_key(), timeout=REQUEST_TIMEOUT_SECONDS)

    years = range(args.start_year, args.end_year + 1)
    log.info(
        "Datasets: %s | zones: %s | years: %s-%s",
        " ".join(args.datasets),
        " ".join(args.zones),
        years[0],
        years[-1],
    )

    counts = {"written": 0, "skipped": 0, "empty": 0, "failed": 0}
    for name in args.datasets:
        for zone in args.zones:
            for year in years:
                try:
                    status = extract_zone_year(
                        DATASETS[name], client, zone, year, args.force
                    )
                    counts[status] += 1
                except requests.HTTPError as e:
                    if e.response is not None and e.response.status_code == 401:
                        log.error(
                            "ENTSO-E rejected the API key (HTTP 401). Check ENTSOE_API_KEY."
                        )
                        return 1
                    log.error("%s %s %s: failed: %s", name, zone, year, e)
                    counts["failed"] += 1
                except Exception:  # keep going with the other zone-years
                    log.exception("%s %s %s: failed", name, zone, year)
                    counts["failed"] += 1

    log.info(
        "Done: %(written)s written, %(skipped)s skipped, %(empty)s empty, %(failed)s failed",
        counts,
    )
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
