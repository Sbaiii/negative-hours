"""Code shared by every dataset: API key, retries, UTC years, resolution, safe writes.

A dataset (prices, generation, load) only has to say how to fetch one zone-year and
turn it into a table; `extract_zone_year` handles skipping, writing and logging.
"""

import logging
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from entsoe import EntsoePandasClient
from entsoe.exceptions import NoMatchingDataError

from pipeline.config import BACKOFF_BASE_SECONDS, MAX_ATTEMPTS, RAW_DIR, REPO_ROOT

log = logging.getLogger("extract")

# 429 = rate limited; 5xx = server side. Anything else (e.g. 401 bad key) won't fix itself.
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
KNOWN_RESOLUTIONS = {15, 30, 60}


@dataclass(frozen=True)
class Dataset:
    """One ENTSO-E dataset and how to turn a zone-year of it into a raw table."""

    name: str  # also the folder name under data/raw/
    # (client, zone, start, end) -> table with ts_utc, zone, ..., resolution_minutes
    fetch: Callable[[EntsoePandasClient, str, pd.Timestamp, pd.Timestamp], pd.DataFrame]


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


def fetch_by_month[T](
    query: Callable[[pd.Timestamp, pd.Timestamp], T],
    start: pd.Timestamp,
    end: pd.Timestamp,
    description: str,
) -> list[T]:
    """Call `query` once per calendar month in [start, end), each with its own retries.

    ENTSO-E serves generation and load at most a month at a time. Retrying per month
    means one failed request doesn't throw away the months already downloaded.
    Months with no data are skipped; raises NoMatchingDataError if every month is empty.
    """
    edges = [start, *pd.date_range(start, end, freq="MS", inclusive="neither"), end]
    results = []
    for month_start, month_end in pairwise(edges):
        try:
            results.append(
                with_retry(
                    lambda s=month_start, e=month_end: query(s, e),
                    description=f"{description} {month_start:%Y-%m}",
                )
            )
        except NoMatchingDataError:
            log.debug("%s %s: no data", description, month_start.strftime("%Y-%m"))
    if not results:
        raise NoMatchingDataError
    return results


def to_utc_range[S: (pd.Series, pd.DataFrame)](
    data: S, start: pd.Timestamp, end: pd.Timestamp
) -> S:
    """Convert to UTC, sort, drop duplicate timestamps and keep [start, end).

    entsoe-py truncates inclusively, so neighbouring years (and months) would
    otherwise share a boundary timestamp.
    """
    data = data.tz_convert("UTC").sort_index()
    data = data[~data.index.duplicated(keep="first")]
    return data[(data.index >= start) & (data.index < end)]


def detect_resolution_minutes(index: pd.DatetimeIndex) -> pd.Series:
    """Length of each period in minutes, inferred from the spacing to its neighbours.

    Uses the smaller of the gap to the previous and to the next timestamp, so a single
    missing period doesn't make its neighbours look like 120-minute periods.
    """
    ts = index.to_series()
    to_prev = ts.diff()
    to_next = -ts.diff(-1)
    step = pd.concat([to_prev, to_next], axis=1).min(axis=1)
    # A lone timestamp has no neighbour; 0 flags it as unknown.
    return (step.dt.total_seconds().fillna(0) // 60).astype("int16")


def series_to_table(
    series: pd.Series, zone: str, value_column: str, label: str
) -> pd.DataFrame:
    """Turn a UTC-indexed series into ts_utc, zone, <value_column>, resolution_minutes.

    Resolution is computed on the series as given, then rows without a value are
    dropped (and counted in the log as missing periods).
    """
    df = pd.DataFrame(
        {
            "ts_utc": series.index.astype("datetime64[us, UTC]"),
            "zone": zone,
            value_column: series.to_numpy(dtype="float64"),
            "resolution_minutes": detect_resolution_minutes(series.index).to_numpy(),
        }
    )
    missing = df[value_column].isna().sum()
    if missing:
        log.warning("%s: %s periods with no value (dropped)", label, missing)
    df = df.dropna(subset=[value_column]).reset_index(drop=True)

    unexpected = sorted(set(df["resolution_minutes"]) - KNOWN_RESOLUTIONS)
    if unexpected:
        log.warning("%s: unexpected resolutions (minutes): %s", label, unexpected)
    return df


def output_path(dataset: str, zone: str, year: int) -> Path:
    return RAW_DIR / dataset / f"zone={zone}" / f"year={year}.parquet"


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    """Write via a temp file so an interrupted run never leaves a half-written Parquet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.tmp")
    df.to_parquet(tmp, index=False)
    tmp.replace(path)


def extract_zone_year(
    dataset: Dataset, client: EntsoePandasClient, zone: str, year: int, force: bool
) -> str:
    """Download one dataset for one zone-year. Returns 'written', 'skipped' or 'empty'."""
    label = f"{dataset.name} {zone} {year}"
    path = output_path(dataset.name, zone, year)
    is_current_year = year == pd.Timestamp.now(tz="UTC").year
    if path.exists() and not force and not is_current_year:
        log.info("%s: already downloaded, skipping", label)
        return "skipped"

    start, end = year_bounds(year)
    log.info("%s: requesting %s → %s", label, start.date(), end.date())
    try:
        df = dataset.fetch(client, zone, start, end)
    except NoMatchingDataError:
        log.warning("%s: no data returned by ENTSO-E", label)
        return "empty"
    if df.empty:
        log.warning("%s: no values in range", label)
        return "empty"

    write_parquet(df, path)
    resolutions = ", ".join(
        f"{r} min" for r in sorted(df["resolution_minutes"].unique())
    )
    log.info(
        "%s: wrote %s rows (%s) → %s",
        label,
        len(df),
        resolutions,
        path.relative_to(REPO_ROOT),
    )
    return "written"
