"""Day-ahead prices → data/raw/prices (ts_utc, zone, price_eur_mwh, resolution_minutes)."""

import pandas as pd
from entsoe import EntsoePandasClient

from pipeline.common import Dataset, finish_table, to_utc_range, with_retry


def fetch_prices(
    client: EntsoePandasClient, zone: str, start: pd.Timestamp, end: pd.Timestamp
) -> pd.DataFrame:
    # entsoe-py splits the year itself, and returns hourly prices before the
    # 2025-10-01 switch to 15-min products, 15-min after.
    prices = with_retry(
        lambda: client.query_day_ahead_prices(zone, start=start, end=end),
        description=f"prices {zone} {start.year}",
    )
    prices = to_utc_range(prices, start, end)
    df = pd.DataFrame(
        {"ts_utc": prices.index, "zone": zone, "price_eur_mwh": prices.to_numpy()}
    )
    # Hours entsoe-py padded with NaN are dropped here and logged as missing periods.
    return finish_table(
        df, ["zone"], "price_eur_mwh", label=f"prices {zone} {start.year}"
    )


PRICES = Dataset(name="prices", fetch=fetch_prices)
