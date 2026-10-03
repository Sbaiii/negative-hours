"""Actual total load → data/raw/load (ts_utc, zone, load_mw, resolution_minutes)."""

import pandas as pd
from entsoe import EntsoePandasClient

from pipeline.common import Dataset, fetch_by_month, finish_table, to_utc_range


def fetch_load(
    client: EntsoePandasClient, zone: str, start: pd.Timestamp, end: pd.Timestamp
) -> pd.DataFrame:
    months = fetch_by_month(
        lambda s, e: client.query_load(zone, start=s, end=e),
        start,
        end,
        description=f"load {zone}",
    )
    load = to_utc_range(pd.concat(frame["Actual Load"] for frame in months), start, end)
    df = pd.DataFrame({"ts_utc": load.index, "zone": zone, "load_mw": load.to_numpy()})
    return finish_table(df, ["zone"], "load_mw", label=f"load {zone} {start.year}")


LOAD = Dataset(name="load", fetch=fetch_load)
