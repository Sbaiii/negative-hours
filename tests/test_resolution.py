"""resolution_minutes must describe the reporting interval, never a gap."""

import logging

import pandas as pd

from pipeline.common import finish_table


def make_table(timestamps, production_type=None) -> pd.DataFrame:
    df = pd.DataFrame(
        {"ts_utc": pd.DatetimeIndex(timestamps), "zone": "FR", "value": 1.0}
    )
    if production_type:
        df.insert(2, "production_type", production_type)
    return df


def hourly(start, periods):
    return pd.date_range(start, periods=periods, freq="h", tz="UTC")


def quarter_hourly(start, periods):
    return pd.date_range(start, periods=periods, freq="15min", tz="UTC")


def resolution_by_ts(out: pd.DataFrame) -> dict[str, int]:
    return {
        ts.strftime("%m-%d %H:%M"): r
        for ts, r in zip(out.ts_utc, out.resolution_minutes)
    }


def test_sparse_series_with_multi_day_gaps_keeps_hourly_resolution(caplog):
    # Pumped storage style: short bursts of generation days apart, plus a lone point.
    ts = [
        *hourly("2024-03-01 06:00", 3),
        *hourly("2024-03-04 18:00", 2),
        pd.Timestamp("2024-03-09 12:00", tz="UTC"),  # alone on its day
        *hourly("2024-03-20 07:00", 4),
    ]
    with caplog.at_level(logging.INFO, logger="extract"):
        out = finish_table(make_table(ts), ["zone"], "value", "test")

    assert len(out) == len(ts)
    assert set(out.resolution_minutes) == {60}
    # Gaps are reported as missing periods, not as resolutions.
    expected_missing = (
        (pd.Timestamp("2024-03-04 18:00") - pd.Timestamp("2024-03-01 08:00"))
        // pd.Timedelta("1h")
        - 1
        + (pd.Timestamp("2024-03-09 12:00") - pd.Timestamp("2024-03-04 19:00"))
        // pd.Timedelta("1h")
        - 1
        + (pd.Timestamp("2024-03-20 07:00") - pd.Timestamp("2024-03-09 12:00"))
        // pd.Timedelta("1h")
        - 1
    )
    assert f"{expected_missing:,} missing periods" in caplog.text


def test_sparse_15_minute_series_lone_point_is_not_read_from_its_gaps():
    # IT_NORD storage style: 15-min bursts, and a lone point days away from them.
    # The gaps around the lone point must not decide its resolution.
    ts = [
        *quarter_hourly("2025-03-01 10:00", 8),
        pd.Timestamp("2025-03-04 13:00", tz="UTC"),
        *quarter_hourly("2025-03-08 10:00", 8),
    ]
    out = finish_table(make_table(ts), ["zone"], "value", "test")
    assert set(out.resolution_minutes) == {15}


def test_lone_point_borrows_the_zone_interval_for_that_day():
    # Hydro Pumped Storage reports one point on a day when the zone is hourly, inside
    # a month that is mostly 15-min. The zone's same-day interval should win.
    nuclear = make_table(
        [*hourly("2024-12-07", 24), *quarter_hourly("2024-12-19", 96 * 12)], "Nuclear"
    )
    pumped = make_table(
        [
            pd.Timestamp("2024-12-07 18:00", tz="UTC"),
            *quarter_hourly("2024-12-19", 96 * 12),
        ],
        "Hydro Pumped Storage",
    )
    out = finish_table(
        pd.concat([nuclear, pumped]), ["zone", "production_type"], "value", "test"
    )
    lone = out[
        (out.production_type == "Hydro Pumped Storage") & (out.ts_utc.dt.day == 7)
    ]
    assert lone.resolution_minutes.tolist() == [60]


def test_one_spacing_on_a_day_does_not_set_the_interval():
    # IT_NORD storage: a 15-min series whose only point on a new day comes 60 min
    # after the previous one (3 missing quarters). The zone is 15-min that day.
    storage = make_table(
        [
            *quarter_hourly("2026-10-02 22:00", 4),
            pd.Timestamp("2026-10-03 00:00", tz="UTC"),
        ],
        "Energy storage",
    )
    solar = make_table(quarter_hourly("2026-10-02 22:00", 13), "Solar")
    out = finish_table(
        pd.concat([storage, solar]), ["zone", "production_type"], "value", "test"
    )
    assert set(out[out.production_type == "Energy storage"].resolution_minutes) == {15}


def test_duplicate_timestamp_is_dropped_keeping_the_first(caplog):
    df = make_table(hourly("2024-01-01", 4))
    duplicate = df.iloc[[2]].assign(value=999.0)
    df = pd.concat([df, duplicate], ignore_index=True)

    with caplog.at_level(logging.WARNING, logger="extract"):
        out = finish_table(df, ["zone"], "value", "test")

    assert len(out) == 4
    assert out.ts_utc.is_unique
    assert 999.0 not in out.value.tolist()
    assert "1 duplicate timestamps" in caplog.text
    assert set(out.resolution_minutes) == {60}


def test_month_switching_from_60_to_15_minutes_mid_month():
    # ES load and generation switched at 2022-05-23 00:00 UTC; 15-min rows dominate
    # the month by count, but the hourly days must stay 60.
    ts = [*hourly("2022-05-01", 22 * 24), *quarter_hourly("2022-05-23", 9 * 96)]
    out = finish_table(make_table(ts), ["zone"], "value", "test")

    switch = pd.Timestamp("2022-05-23", tz="UTC")
    assert set(out[out.ts_utc < switch].resolution_minutes) == {60}
    assert set(out[out.ts_utc >= switch].resolution_minutes) == {15}


def test_switch_inside_a_utc_day_is_caught():
    # Day-ahead prices went to 15 min at CET midnight = 2025-09-30 22:00 UTC.
    ts = [*hourly("2025-09-30", 22), *quarter_hourly("2025-09-30 22:00", 16)]
    by_ts = resolution_by_ts(finish_table(make_table(ts), ["zone"], "value", "test"))

    assert by_ts["09-30 21:00"] == 60
    assert by_ts["09-30 22:00"] == 15
    assert by_ts["09-30 23:45"] == 15


def test_single_missing_quarter_is_a_gap_not_a_30_minute_period(caplog):
    ts = quarter_hourly("2025-01-01", 96).delete([10, 12])  # 2 isolated holes
    with caplog.at_level(logging.INFO, logger="extract"):
        out = finish_table(make_table(ts), ["zone"], "value", "test")

    assert set(out.resolution_minutes) == {15}
    assert "2 missing periods" in caplog.text


def test_last_row_of_the_file_keeps_its_resolution():
    # The last hour of a UTC-year file has no next timestamp.
    ts = hourly("2024-12-31 20:00", 4)
    out = finish_table(make_table(ts), ["zone"], "value", "test")
    assert out.resolution_minutes.tolist() == [60, 60, 60, 60]


def test_rows_without_a_value_become_gaps(caplog):
    # entsoe-py pads missing hours in prices with NaN.
    df = make_table(hourly("2024-01-01", 6))
    df.loc[2, "value"] = float("nan")
    with caplog.at_level(logging.INFO, logger="extract"):
        out = finish_table(df, ["zone"], "value", "test")

    assert len(out) == 5
    assert set(out.resolution_minutes) == {60}
    assert "1 missing periods" in caplog.text
