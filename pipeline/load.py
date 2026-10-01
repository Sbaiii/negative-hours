"""Actual total load → data/raw/load (ts_utc, zone, load_mw, resolution_minutes)."""

import pandas as pd
from entsoe import EntsoePandasClient

from pipeline.common import Dataset, fetch_by_month, series_to_table, to_utc_range


def fetch_load(
    client: EntsoePandasClient, zone: str, start: pd.Timestamp, end: pd.Timestamp
) -> pd.DataFrame:
    months = fetch_by_month(
        lambda s, e: client.query_load(zone, start=s, end=e),
        start,
        end,
        description=f"load {zone}",
    )
    load = pd.concat(frame["Actual Load"] for frame in months)
    return series_to_table(
        to_utc_range(load, start, end),
        zone,
        "load_mw",
        label=f"load {zone} {start.year}",
    )


LOAD = Dataset(name="load", fetch=fetch_load)
