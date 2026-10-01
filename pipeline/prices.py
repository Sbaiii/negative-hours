"""Day-ahead prices → data/raw/prices (ts_utc, zone, price_eur_mwh, resolution_minutes)."""

import pandas as pd
from entsoe import EntsoePandasClient

from pipeline.common import Dataset, series_to_table, to_utc_range, with_retry


def fetch_prices(
    client: EntsoePandasClient, zone: str, start: pd.Timestamp, end: pd.Timestamp
) -> pd.DataFrame:
    # entsoe-py splits the year itself, and returns hourly prices before the
    # 2025-10-01 switch to 15-min products, 15-min after.
    prices = with_retry(
        lambda: client.query_day_ahead_prices(zone, start=start, end=end),
        description=f"prices {zone} {start.year}",
    )
    # Resolution is read before gaps are dropped: entsoe-py pads missing hours with NaN.
    return series_to_table(
        to_utc_range(prices, start, end),
        zone,
        "price_eur_mwh",
        label=f"prices {zone} {start.year}",
    )


PRICES = Dataset(name="prices", fetch=fetch_prices)
