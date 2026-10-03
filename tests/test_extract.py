"""End-to-end checks of one zone-year download, against a fake ENTSO-E client."""

import pandas as pd
import pytest
import requests
from entsoe.exceptions import NoMatchingDataError

from pipeline import common
from pipeline.generation import GENERATION, actual_aggregated
from pipeline.load import LOAD
from pipeline.prices import PRICES

TZ = "Europe/Madrid"


@pytest.fixture(autouse=True)
def isolated_output(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "RAW_DIR", tmp_path / "data" / "raw")
    monkeypatch.setattr(common, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(common, "BACKOFF_BASE_SECONDS", 0)


def local_range(start, end, freq):
    """Like entsoe-py: local time zone, end included."""
    return pd.date_range(start.tz_convert(TZ), end.tz_convert(TZ), freq=freq)


class FakeClient:
    def __init__(self, fail_first=0):
        self.calls = 0
        self.fail_first = fail_first

    def _call(self):
        self.calls += 1
        if self.calls <= self.fail_first:
            response = requests.Response()
            response.status_code = 503
            raise requests.HTTPError(response=response)

    def query_day_ahead_prices(self, zone, start, end):
        self._call()
        return pd.Series(50.0, index=local_range(start, end, "h"))

    def query_load(self, zone, start, end):
        self._call()
        if start.month == 6:
            raise NoMatchingDataError
        return pd.DataFrame(
            {"Actual Load": 30_000.0}, index=local_range(start, end, "15min")
        )

    def query_generation(self, zone, start, end):
        self._call()
        quarters = local_range(start, end, "15min")
        hours = local_range(start, end, "h")
        if start.month == 2:  # one type only: entsoe-py returns a Series
            return pd.Series(100.0, index=quarters, name="Solar")
        if start.month == 3:  # a type with consumption: MultiIndex columns
            return pd.DataFrame(
                {
                    ("Solar", "Actual Aggregated"): pd.Series(100.0, index=quarters),
                    ("Hydro Pumped Storage", "Actual Aggregated"): pd.Series(
                        5.0, index=hours
                    ),
                    ("Hydro Pumped Storage", "Actual Consumption"): pd.Series(
                        7.0, index=hours
                    ),
                }
            )
        return pd.DataFrame(
            {
                "Solar": pd.Series(100.0, index=quarters),
                "Biomass": pd.Series(10.0, index=hours),
            }
        )


def test_actual_aggregated_handles_every_column_shape():
    idx = pd.date_range("2024-01-01", periods=2, freq="h", tz="UTC")
    multi = pd.DataFrame(
        {
            ("Solar", "Actual Aggregated"): [1.0, 2.0],
            ("Hydro", "Actual Consumption"): [3.0, 4.0],
        },
        index=idx,
    )
    flat = pd.DataFrame({"Solar": [1.0, 2.0]}, index=idx)
    single = pd.Series([1.0, 2.0], index=idx, name="Solar")

    for raw in (multi, flat, single):
        frame, _ = actual_aggregated(raw)
        assert list(frame.columns) == ["Solar"]
    assert actual_aggregated(multi)[1] == {"Hydro"}


def test_generation_zone_year():
    client = FakeClient(fail_first=1)
    assert (
        common.extract_zone_year(GENERATION, client, "ES", 2024, force=False)
        == "written"
    )
    assert client.calls == 12 + 1  # one per month, plus one retry

    df = pd.read_parquet(common.output_path("generation", "ES", 2024))
    assert list(df.columns) == [
        "ts_utc",
        "zone",
        "production_type",
        "generation_mw",
        "resolution_minutes",
    ]
    assert set(df.production_type) == {"Solar", "Biomass", "Hydro Pumped Storage"}
    assert 7.0 not in df.generation_mw.tolist()  # consumption is not kept
    assert not df.duplicated(["zone", "production_type", "ts_utc"]).any()
    assert df.ts_utc.min() == pd.Timestamp("2024-01-01", tz="UTC")
    assert df.ts_utc.max() < pd.Timestamp("2025-01-01", tz="UTC")
    resolution = df.groupby("production_type").resolution_minutes.unique()
    assert list(resolution["Solar"]) == [15]
    assert list(resolution["Biomass"]) == [60]
    # Pumped storage only reports in March, yet still reads as hourly.
    assert list(resolution["Hydro Pumped Storage"]) == [60]


def test_load_zone_year_with_an_empty_month():
    assert (
        common.extract_zone_year(LOAD, FakeClient(), "ES", 2024, force=False)
        == "written"
    )
    df = pd.read_parquet(common.output_path("load", "ES", 2024))
    assert list(df.columns) == ["ts_utc", "zone", "load_mw", "resolution_minutes"]
    assert set(df.resolution_minutes) == {15}  # the June gap is not a resolution


def test_prices_skip_force_and_current_year():
    client = FakeClient()
    assert (
        common.extract_zone_year(PRICES, client, "ES", 2024, force=False) == "written"
    )
    assert (
        common.extract_zone_year(PRICES, client, "ES", 2024, force=False) == "skipped"
    )
    assert common.extract_zone_year(PRICES, client, "ES", 2024, force=True) == "written"

    this_year = pd.Timestamp.now(tz="UTC").year
    calls = client.calls
    common.extract_zone_year(PRICES, client, "ES", this_year, force=False)
    common.extract_zone_year(PRICES, client, "ES", this_year, force=False)
    assert client.calls == calls + 2  # never skipped
