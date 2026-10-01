"""Actual generation per production type → data/raw/generation (long format).

Columns: ts_utc, zone, production_type, generation_mw, resolution_minutes

entsoe-py returns one column per production type. When a type also reports its own
consumption (e.g. pumped storage while pumping), the columns become a MultiIndex of
(production type, "Actual Aggregated" | "Actual Consumption"). That can differ from
one month to the next, so each month is normalised before months are combined.
We keep only "Actual Aggregated" (what plants feed into the grid).
"""

import logging

import pandas as pd
from entsoe import EntsoePandasClient

from pipeline.common import Dataset, fetch_by_month, series_to_table, to_utc_range

log = logging.getLogger("extract")

GENERATED = "Actual Aggregated"
CONSUMED = "Actual Consumption"


def actual_aggregated(raw: pd.DataFrame | pd.Series) -> tuple[pd.DataFrame, set[str]]:
    """One column per production type, generation only.

    Returns the frame and the set of types whose consumption column was dropped.
    """
    if isinstance(raw, pd.Series):  # entsoe-py squeezes a single-type result
        raw = raw.to_frame()

    kept: dict[str, pd.Series] = {}
    dropped: set[str] = set()
    for column in raw.columns:
        # Flat columns are plain type names and always mean "Actual Aggregated".
        production_type, metric = (
            column if isinstance(column, tuple) else (column, GENERATED)
        )
        if metric == CONSUMED:
            dropped.add(production_type)
        elif metric == GENERATED:
            kept[production_type] = raw[column]
    return pd.DataFrame(kept, index=raw.index), dropped


def fetch_generation(
    client: EntsoePandasClient, zone: str, start: pd.Timestamp, end: pd.Timestamp
) -> pd.DataFrame:
    label = f"generation {zone} {start.year}"
    months = fetch_by_month(
        lambda s, e: actual_aggregated(client.query_generation(zone, start=s, end=e)),
        start,
        end,
        description=f"generation {zone}",
    )
    wide = to_utc_range(pd.concat(frame for frame, _ in months), start, end)
    dropped = set().union(*(d for _, d in months))

    tables = []
    for production_type in sorted(wide.columns):
        # NaNs in the wide frame are mostly alignment between types reporting at
        # different times, so drop them first and read resolution per type.
        series = wide[production_type].dropna()
        if series.empty:
            continue
        table = series_to_table(
            series, zone, "generation_mw", label=f"{label} {production_type}"
        )
        table.insert(2, "production_type", production_type)
        tables.append(table)

    types = [t["production_type"].iat[0] for t in tables]
    log.info("%s: %s production types: %s", label, len(types), ", ".join(types))
    if dropped:
        log.info(
            "%s: dropped consumption columns for: %s", label, ", ".join(sorted(dropped))
        )
    if not tables:
        return pd.DataFrame(
            columns=[
                "ts_utc",
                "zone",
                "production_type",
                "generation_mw",
                "resolution_minutes",
            ]
        )
    return pd.concat(tables, ignore_index=True)


GENERATION = Dataset(name="generation", fetch=fetch_generation)
