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
STANDARD_RESOLUTIONS = (15, 30, 60)
MIN_ROWS_PER_DAY = 3  # see add_resolution, step 3


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


def add_resolution(df: pd.DataFrame, keys: list[str], label: str) -> pd.DataFrame:
    """Add resolution_minutes: the interval a series is reported at, never a gap.

    `keys` identify one series (["zone"], or ["zone", "production_type"]).
    1. Spacings between consecutive timestamps of 60 min or less are evidence of the
       reporting interval; longer spacings are gaps and are ignored.
    2. Each UTC day gets its most common spacing, snapped to 15/30/60. Days rather than
       months, because intervals change mid-month (ES load and generation went from
       60 to 15 min on 2022-05-23).
    3. A series needs at least 3 timestamps on a day to set that day's value; with
       fewer, its one spacing is as likely a gap as the interval. Such days (and days
       with no usable spacing) borrow the value of the whole zone that day (all types
       in a zone switch together), then of their own month, then of the zone that month.
    4. If a row's spacing to the next timestamp is a standard interval shorter than its
       day's value, the shorter one wins. This catches switches that happen inside a
       UTC day (day-ahead prices went to 15 min at CET midnight, 22:00 UTC). Gaps
       only ever make spacings longer, so they can't trigger it.
    Missing periods are counted from the gaps and logged.
    """
    df = df.sort_values([*keys, "ts_utc"], ignore_index=True)
    df["_day"] = df["ts_utc"].dt.floor("D")
    df["_month"] = df["ts_utc"].dt.tz_localize(None).dt.to_period("M")
    rows_that_day = df.groupby([*keys, "_day"])["ts_utc"].transform("size")

    to_next = -df.groupby(keys)["ts_utc"].diff(-1).dt.total_seconds() / 60
    from_prev = df.groupby(keys)["ts_utc"].diff().dt.total_seconds() / 60
    # Each spacing counts for the rows on both sides of it, so the last row before a
    # gap (or the end of the file) still has evidence.
    evidence = pd.concat([df.assign(_step=to_next), df.assign(_step=from_prev)])
    evidence = evidence[evidence["_step"] <= max(STANDARD_RESOLUTIONS)]

    resolution = pd.Series(float("nan"), index=df.index)
    enough_rows = evidence.index.map(rows_that_day >= MIN_ROWS_PER_DAY)
    levels = [
        ([*keys, "_day"], evidence[enough_rows]),
        (["zone", "_day"], evidence),
        ([*keys, "_month"], evidence),
        (["zone", "_month"], evidence),
    ]
    for by, source in levels:
        most_common = source.groupby(by, observed=True)["_step"].agg(
            lambda s: s.mode().min()
        )
        resolution = resolution.fillna(df[by].join(most_common, on=by)["_step"])

    unknown = resolution.isna()
    if unknown.any():
        log.warning(
            "%s: %s rows with no way to tell their interval (dropped)",
            label,
            unknown.sum(),
        )
    resolution = resolution.map(
        lambda m: min(STANDARD_RESOLUTIONS, key=lambda r: abs(r - m)),
        na_action="ignore",
    )
    finer = to_next.isin(STANDARD_RESOLUTIONS) & (to_next < resolution)
    df["resolution_minutes"] = resolution.mask(finer, to_next)

    df["_missing"] = (to_next / df["resolution_minutes"]).round() - 1
    df = df[~unknown]
    log_gaps(df, keys, label)
    return df.drop(columns=["_day", "_month", "_missing"]).astype(
        {"resolution_minutes": "int16"}
    )


def log_gaps(df: pd.DataFrame, keys: list[str], label: str) -> None:
    """Log how many reporting periods are missing between the first and last row."""
    missing = df[df["_missing"] > 0].groupby(keys)["_missing"].sum().astype(int)
    if missing.empty:
        return
    if keys == ["zone"]:
        log.info("%s: %s missing periods (gaps)", label, f"{missing.sum():,}")
    else:
        detail = ", ".join(
            f"{key[-1]} {n:,}"
            for key, n in missing.sort_values(ascending=False).items()
        )
        log.info("%s: missing periods (gaps) by series: %s", label, detail)


def finish_table(
    df: pd.DataFrame, keys: list[str], value_column: str, label: str
) -> pd.DataFrame:
    """Shared last step for every dataset: drop empties and duplicates, add resolution.

    `df` has ts_utc (UTC), the `keys` columns and `value_column`.
    """
    df = df.dropna(subset=[value_column])
    duplicated = df.duplicated([*keys, "ts_utc"], keep="first")
    if duplicated.any():
        log.warning(
            "%s: %s duplicate timestamps (kept the first)", label, duplicated.sum()
        )
        df = df[~duplicated]
    df = df.astype({"ts_utc": "datetime64[us, UTC]", value_column: "float64"})
    df = add_resolution(df, keys, label)
    return df[["ts_utc", *keys, value_column, "resolution_minutes"]].reset_index(
        drop=True
    )


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
