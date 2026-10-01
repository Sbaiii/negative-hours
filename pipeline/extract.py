"""Pull ENTSO-E day-ahead prices and save them as Parquet, one file per zone per year.

Output: data/raw/prices/zone=<ZONE>/year=<YYYY>.parquet
Columns: ts_utc, zone, price_eur_mwh, resolution_minutes

Years are UTC calendar years. The current year is always re-downloaded because it is
still filling up; past years are skipped if their file exists (use --force to redo them).

Usage:
    uv run python -m pipeline.extract
    uv run python -m pipeline.extract --zones ES DE_LU --start-year 2023 --force
"""

import argparse
import logging
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from entsoe import EntsoePandasClient
from entsoe.exceptions import NoMatchingDataError

from pipeline.config import (
    BACKOFF_BASE_SECONDS,
    DEFAULT_START_YEAR,
    MAX_ATTEMPTS,
    RAW_PRICES_DIR,
    REPO_ROOT,
    REQUEST_TIMEOUT_SECONDS,
    ZONES,
)

log = logging.getLogger("extract")

# 429 = rate limited; 5xx = server side. Anything else (e.g. 401 bad key) won't fix itself.
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
KNOWN_RESOLUTIONS = {15, 30, 60}


def parse_args() -> argparse.Namespace:
    current_year = pd.Timestamp.now(tz="UTC").year
    parser = argparse.ArgumentParser(
        description="Download ENTSO-E day-ahead prices to Parquet."
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


def get_api_key() -> str:
    load_dotenv()
    api_key = os.getenv("ENTSOE_API_KEY", "").strip()
    if not api_key:
        sys.exit(
            "ENTSOE_API_KEY is missing. Copy .env.example to .env and paste your "
            "ENTSO-E security token after ENTSOE_API_KEY= (see README, 'Run it locally')."
        )
    return api_key


def with_retry[T](call: Callable[[], T], description: str) -> T:
    """Run `call`, retrying with exponential backoff on network errors and retryable HTTP codes."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return call()
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status not in RETRYABLE_STATUS_CODES or attempt == MAX_ATTEMPTS:
                raise
            reason = f"HTTP {status}"
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt == MAX_ATTEMPTS:
                raise
            reason = type(e).__name__
        wait = BACKOFF_BASE_SECONDS * 2 ** (attempt - 1)
        log.warning(
            "%s: %s, retrying in %ss (attempt %s/%s)",
            description,
            reason,
            wait,
            attempt + 1,
            MAX_ATTEMPTS,
        )
        time.sleep(wait)
    raise AssertionError("unreachable")


def year_bounds(year: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Start and (exclusive) end of a UTC year, capped so we never ask for data past tomorrow."""
    start = pd.Timestamp(year=year, month=1, day=1, tz="UTC")
    end = pd.Timestamp(year=year + 1, month=1, day=1, tz="UTC")
    # Day-ahead prices are published for tomorrow, so stop at the end of tomorrow.
    latest = pd.Timestamp.now(tz="UTC").normalize() + pd.Timedelta(days=2)
    return start, min(end, latest)


def detect_resolution_minutes(index: pd.DatetimeIndex) -> pd.Series:
    """Length of each period in minutes, inferred from the spacing to its neighbours.

    Uses the smaller of the gap to the previous and to the next timestamp, so a single
    missing period doesn't make its neighbours look like 120-minute periods.
    """
    ts = index.to_series()
    to_prev = ts.diff()
    to_next = -ts.diff(-1)
    step = pd.concat([to_prev, to_next], axis=1).min(axis=1)
    return (step.dt.total_seconds() // 60).astype("int16")


def to_frame(
    prices: pd.Series, zone: str, start: pd.Timestamp, end: pd.Timestamp
) -> pd.DataFrame:
    """Turn the entsoe-py price series into the raw table layout, in UTC."""
    prices = prices.tz_convert("UTC").sort_index()
    prices = prices[~prices.index.duplicated(keep="first")]
    # entsoe-py truncates inclusively; keep [start, end) so years don't overlap.
    prices = prices[(prices.index >= start) & (prices.index < end)]

    df = pd.DataFrame(
        {
            "ts_utc": prices.index,
            "zone": zone,
            "price_eur_mwh": prices.to_numpy(dtype="float64"),
            # Computed before dropping gaps: entsoe-py pads missing hours with NaN rows.
            "resolution_minutes": detect_resolution_minutes(prices.index).to_numpy(),
        }
    )
    df["ts_utc"] = df["ts_utc"].astype("datetime64[us, UTC]")

    missing = df["price_eur_mwh"].isna().sum()
    if missing:
        log.warning("%s: %s periods with no price (dropped)", zone, missing)
    df = df.dropna(subset=["price_eur_mwh"]).reset_index(drop=True)

    unexpected = sorted(set(df["resolution_minutes"]) - KNOWN_RESOLUTIONS)
    if unexpected:
        log.warning("%s: unexpected resolutions (minutes): %s", zone, unexpected)
    return df


def output_path(zone: str, year: int) -> Path:
    return RAW_PRICES_DIR / f"zone={zone}" / f"year={year}.parquet"


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    """Write via a temp file so an interrupted run never leaves a half-written Parquet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.tmp")
    df.to_parquet(tmp, index=False)
    tmp.replace(path)


def extract_zone_year(
    client: EntsoePandasClient, zone: str, year: int, force: bool
) -> str:
    """Download one zone-year. Returns 'written', 'skipped' or 'empty'."""
    path = output_path(zone, year)
    is_current_year = year == pd.Timestamp.now(tz="UTC").year
    if path.exists() and not force and not is_current_year:
        log.info("%s %s: already downloaded, skipping", zone, year)
        return "skipped"

    start, end = year_bounds(year)
    log.info("%s %s: requesting %s → %s", zone, year, start.date(), end.date())
    try:
        prices = with_retry(
            lambda: client.query_day_ahead_prices(zone, start=start, end=end),
            description=f"{zone} {year}",
        )
    except NoMatchingDataError:
        log.warning("%s %s: no data returned by ENTSO-E", zone, year)
        return "empty"

    df = to_frame(prices, zone, start, end)
    if df.empty:
        log.warning("%s %s: no prices in range", zone, year)
        return "empty"

    write_parquet(df, path)
    resolutions = ", ".join(
        f"{r} min" for r in sorted(df["resolution_minutes"].unique())
    )
    log.info(
        "%s %s: wrote %s rows (%s) → %s",
        zone,
        year,
        len(df),
        resolutions,
        path.relative_to(REPO_ROOT),
    )
    return "written"


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    args = parse_args()
    client = EntsoePandasClient(api_key=get_api_key(), timeout=REQUEST_TIMEOUT_SECONDS)

    years = range(args.start_year, args.end_year + 1)
    log.info("Zones: %s | years: %s-%s", " ".join(args.zones), years[0], years[-1])

    counts = {"written": 0, "skipped": 0, "empty": 0, "failed": 0}
    for zone in args.zones:
        for year in years:
            try:
                counts[extract_zone_year(client, zone, year, args.force)] += 1
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 401:
                    log.error(
                        "ENTSO-E rejected the API key (HTTP 401). Check ENTSOE_API_KEY."
                    )
                    return 1
                log.error("%s %s: failed: %s", zone, year, e)
                counts["failed"] += 1
            except Exception:  # keep going with the other zone-years
                log.exception("%s %s: failed", zone, year)
                counts["failed"] += 1

    log.info(
        "Done: %(written)s written, %(skipped)s skipped, %(empty)s empty, %(failed)s failed",
        counts,
    )
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
