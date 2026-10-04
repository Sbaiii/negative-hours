"""Draft the quoted-numbers registry for a snapshot: map every number in the docs to its source.

    uv run python analysis/outputs/snapshots/build_registry.py 2026-10-02

For each number in the README and finding notes, it looks for a snapshot cell that
prints the same way (as written, rounded, or as a percentage), restricted to the
zones and years named on the same line (or in the table row and column header). The
first match is written to <snapshot>/quoted_numbers.csv as an explicit table, row
filter, formula, format and position, so tests/test_quoted_numbers.py can recompute
it. Numbers it can't match are taken from MANUAL below (constants, external figures,
derived values) or listed for review: the registry is a reviewed record, not a guess
that is re-made on every run.
"""

import csv
import re
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "tests"))
from test_quoted_numbers import DOCS, numbers_in, tokens

ZONE_WORDS = {
    "BE": ["BE", "Belgium"],
    "DE_LU": ["DE_LU", "Germany", "German"],
    "ES": ["ES", "Spain", "Spanish"],
    "FR": ["FR", "France", "French"],
    "IT_NORD": ["IT_NORD", "North Italy", "Italian"],
    "NL": ["NL", "Netherlands", "Dutch"],
    "PL": ["PL", "Poland", "Polish"],
    "PT": ["PT", "Portugal", "Portuguese"],
}
KEYS = [
    "zone",
    "local_year",
    "local_month",
    "battery_duration_h",
    "season",
    "local_hour",
    "month",
    "scope",
    "years",
    "year",
]
YTD_TABLES = {"fct_ytd_comparison", "q3_hourly_resolve_ytd"}
# Which snapshot tables a question's numbers may come from (limits chance matches).
SECTION_TABLES = {
    "Q1": ("fct_negative_hours", "fct_ytd_comparison", "q1_"),
    "Q2": ("fct_capture_prices", "fct_solar_monthly", "fct_ytd_comparison", "q2_"),
    "Q3": ("fct_battery_arbitrage", "fct_ytd_comparison", "fct_negative_hours", "q3_"),
    "Q4": ("fct_ev_charging", "fct_hourly_profile", "fct_ytd_comparison", "q4_"),
}


# Table column headers -> (table prefix, formula prefix) the cell must come from.
HEADER_HINTS = [
    (
        r"^Hours with|^Negative hours$|^20\d\d$",
        ("fct_negative_hours", "negative_hours"),
        "Q1",
    ),
    (r"1 Jan to 2 Oct", ("fct_ytd_comparison", "negative_hours"), "Q1"),
    (
        r"Avg price when negative",
        ("fct_negative_hours", "avg_price_negative_periods"),
        "Q1",
    ),
    (r"Lowest price", ("fct_negative_hours", "min_price"), "Q1"),
    (
        r"^Capture rate 20\d\d$|^Solar rate$|^Capture rate$|^2025 rate$",
        ("fct_capture_prices", "solar_capture_rate"),
        "Q2",
    ),
    (r"1 Jan to 2 Oct", ("fct_ytd_comparison", "solar_capture_rate"), "Q2"),
    (r"Solar capture", ("fct_capture_prices", "solar_capture_price"), "Q2"),
    (r"Baseload", ("fct_capture_prices", "baseload_price"), "Q2"),
    (r"^Solar share$|^→ 2025 share$", ("fct_capture_prices", "solar_share"), "Q2"),
    (r"^Wind rate$", ("fct_capture_prices", "wind_capture_rate"), "Q2"),
    (r"^Wind capture", ("fct_capture_prices", "wind_capture_price"), "Q2"),
    (r"^Wind share$", ("fct_capture_prices", "wind_share"), "Q2"),
    (r"^Seasonal", ("q2_capture_rate_decomposition", "seasonal"), "Q2"),
    (r"^Within-month", ("q2_capture_rate_decomposition", "within_month"), "Q2"),
    (r"^Capture rate 2021 → 2022", ("fct_capture_prices", "solar_capture_rate"), "Q2"),
    (
        r"^r \(monthly",
        ("q2_capture_rate_decomposition", "r_month_price_vs_solar"),
        "Q2",
    ),
    (r"^r, own share", ("q2_regional_correlations", "pearson_own"), "Q2"),
    (r"^r, regional share", ("q2_regional_correlations", "pearson_region"), "Q2"),
    (r"^Spearman own", ("q2_regional_correlations", "spearman_own"), "Q2"),
    (r"^Spearman regional", ("q2_regional_correlations", "spearman_region"), "Q2"),
    (
        r"^r between the two shares",
        ("q2_regional_correlations", "r_own_vs_region_share"),
        "Q2",
    ),
    (r"^n$", ("q2_regional_correlations", "n"), "Q2"),
    (r"^Revenue €/MW$|^20\d\d$", ("fct_battery_arbitrage", "revenue_eur_per_mw"), "Q3"),
    (r"^Per day$", ("fct_battery_arbitrage", "avg_daily_revenue_eur_per_mw"), "Q3"),
    (
        r"^Spread captured",
        ("fct_battery_arbitrage", "avg_spread_captured_eur_mwh"),
        "Q3",
    ),
    (
        r"^Rule of thumb",
        ("fct_battery_arbitrage", "heuristic_revenue_eur_per_mw"),
        "Q3",
    ),
    (r"^LP uplift", ("fct_battery_arbitrage", "lp_uplift"), "Q3"),
    (r"^1 Jan to 2 Oct", ("fct_ytd_comparison", "battery_revenue_eur_per_mw"), "Q3"),
    (r"^2026 on hourly prices", ("q3_hourly_resolve_ytd", "ytd_2026_hourly"), "Q3"),
    (r"^Change$", ("q3_hourly_resolve_ytd", "change_vs_2025_native"), "Q3"),
    (r"^Change, hourly", ("q3_hourly_resolve_ytd", "change_vs_2025_hourly"), "Q3"),
    (r"^Added by 15-min", ("q3_hourly_resolve_ytd", "added_by_15min"), "Q3"),
    (r"^Avg price then", ("q4_cheapest_hour", "mean_price"), "Q4"),
    (r"^18:00 €/yr", ("fct_ev_charging", "immediate_eur_per_year"), "Q4"),
    (r"^Overnight €/yr", ("fct_ev_charging", "overnight_eur_per_year"), "Q4"),
    (r"^Smart €/yr", ("fct_ev_charging", "smart_eur_per_year"), "Q4"),
    (r"^Smart saving$", ("fct_ev_charging", "smart_savings_eur_per_year"), "Q4"),
    (r"^Share$", ("fct_ev_charging", "smart_savings_share"), "Q4"),
    (r"^Price paid", ("fct_ev_charging", "_price_eur_mwh"), "Q4"),
    (r"^Overnight 20\d\d$", ("fct_ev_charging", "overnight_savings_share"), "Q4"),
    (r"^Smart 20\d\d$", ("fct_ev_charging", "smart_savings_share"), "Q4"),
    (
        r"^Overnight 20\d\d window",
        ("fct_ytd_comparison", "ev_overnight_saving_share"),
        "Q4",
    ),
    (r"^Smart 20\d\d window", ("fct_ytd_comparison", "ev_smart_saving_share"), "Q4"),
]


def hint_for(header: str, section: str | None):
    for pattern, target, sec in HEADER_HINTS:
        if sec == section and re.search(pattern, header):
            return target
    return None


def zones_in(text: str) -> set[str]:
    return {
        z
        for z, words in ZONE_WORDS.items()
        if any(re.search(rf"\b{re.escape(w)}\b", text) for w in words)
    }


def years_in(text: str) -> set[int]:
    return {int(y) for y in re.findall(r"\b(20[12]\d)\b", text)}


def formats(value: float, column: str) -> list[tuple[str, str, str]]:
    """(text, expr, fmt) ways the value may be written."""
    out = []
    for d in (2, 1, 0, 3):
        t = f"{value:,.{d}f}"
        out.append((t.rstrip("0").rstrip(".") if d else t, column, f"num{d}"))
    for d in (2, 1):  # with trailing zeros, e.g. 63.20
        out.append((f"{value:,.{d}f}", column, f",.{d}f"))
    if abs(value) <= 3 and re.search(
        r"rate|share|coverage|completeness|uplift|added|change|^r$|pearson|spearman|^r_",
        column,
    ):
        for d in (1, 0):
            out.append((f"{value * 100:.{d}f}", f"{column} * 100", f".{d}f"))
            out.append((f"{value * 100:+.{d}f}", f"{column} * 100", f"+.{d}f"))
    if "eur_per_mw" in column and abs(value) >= 1000:
        for d in (1, 0):
            out.append((f"{value / 1000:.{d}f}", f"{column} / 1000", f".{d}f"))
    if re.search(r"^r$|pearson|spearman|^r_|seasonal|within_month", column):
        for d in (2, 3):
            out.append((f"{value:+.{d}f}", column, f"+.{d}f"))
    return [(t.replace("-", "−"), e, f) for t, e, f in out]


def load_cells(snapshot: Path) -> list[dict]:
    cells = []
    for path in sorted(snapshot.glob("*.csv")):
        if path.name == "quoted_numbers.csv":
            continue
        df = pd.read_csv(path)
        keys = [k for k in KEYS if k in df.columns]
        for _, row in df.iterrows():
            key = {k: row[k] for k in keys if pd.notna(row[k])}
            for col in df.columns:
                if (
                    col in keys
                    or not pd.api.types.is_number(row[col])
                    or pd.isna(row[col])
                ):
                    continue
                for text, expr, fmt in formats(float(row[col]), col):
                    cells.append(
                        {
                            "table": path.stem,
                            "key": key,
                            "text": text,
                            "expr": expr,
                            "fmt": fmt,
                        }
                    )
    return cells


def where(key: dict) -> str:
    parts = []
    for k, v in key.items():
        v = int(v) if isinstance(v, float) and v.is_integer() else v
        parts.append(f"{k}={v}")
    return ";".join(parts)


def table_context(lines: list[str], i: int) -> tuple[str, list[str]] | None:
    """For a table row: (header line, header cells)."""
    j = i
    while j > 0 and lines[j - 1].startswith("|"):
        j -= 1
    if (
        j + 1 < len(lines)
        and lines[j].startswith("|")
        and set(lines[j + 1]) <= set("|-: ")
    ):
        return lines[j], [c.strip() for c in lines[j].strip("|").split("|")]
    return None


def candidates(cells, number, zones, years, ytd, section=None, target=None):
    hits = [c for c in cells if c["text"].lstrip("+") == number.lstrip("+")]
    if section in SECTION_TABLES:
        hits = [c for c in hits if c["table"].startswith(SECTION_TABLES[section])]
    if target:  # a table column pinned to a mart column
        table, expr = target
        hits = [
            c
            for c in hits
            if c["table"].startswith(table)
            and (c["expr"].startswith(expr) or expr in c["expr"])
        ]
    if zones:
        hits = [c for c in hits if c["key"].get("zone") in zones] or [
            c for c in hits if "zone" not in c["key"]
        ]
    if years:
        y = [
            c
            for c in hits
            if int(c["key"].get("local_year", c["key"].get("year", 0)) or 0) in years
        ]
        hits = y or hits
    if ytd is not None:
        pref = [c for c in hits if (c["table"] in YTD_TABLES) == ytd]
        hits = pref or hits
    return hits


def build(snapshot: Path, manual: list[dict]) -> list[dict]:
    cells = load_cells(snapshot)
    rows, unmatched = [], []
    for doc in DOCS:
        rel = doc.relative_to(REPO_ROOT).as_posix()
        lines = doc.read_text(encoding="utf-8").split("\n")
        section = (
            re.match(r"(Q\d)", doc.name).group(1)
            if re.match(r"Q\d", doc.name)
            else None
        )
        for i, line in enumerate(lines):
            heading = re.match(r"### (Q\d)", line)
            if heading and doc.name == "README.md":
                section = heading.group(1)
            if line.startswith("**Question:**"):
                continue
            wanted = numbers_in(line)
            if not wanted:
                continue
            all_tokens = tokens(line)
            used = set()
            # Manual entries without a number apply, in order, to the numbers on the line.
            in_order = [
                m
                for m in manual
                if m["doc"] == rel and m["quote"] in line and m["number"] is None
            ]
            ctx = table_context(lines, i) if line.startswith("|") else None
            for j, number in enumerate(wanted):
                # position of this token in the line (first unused occurrence)
                pos = next(
                    k for k, t in enumerate(all_tokens) if t == number and k not in used
                )
                used.add(pos)
                m = next(
                    (
                        m
                        for m in manual
                        if m["doc"] == rel
                        and m["quote"] in line
                        and m["number"] == number
                    ),
                    None,
                )
                if m is None and j < len(in_order):
                    m = in_order[j]
                if m:
                    rows.append(
                        {
                            "doc": rel,
                            "quote": line,
                            "table": m["table"],
                            "where": m.get("where", ""),
                            "expr": m["expr"],
                            "fmt": m.get("fmt", ""),
                            "agg": m.get("agg", ""),
                            "position": pos + 1,
                        }
                    )
                    continue
                if ctx:
                    _, head_cells = ctx
                    cells_row = [c.strip() for c in line.strip("|").split("|")]
                    col = next(
                        (k for k, c in enumerate(cells_row) if number in tokens(c)), 0
                    )
                    head = head_cells[col] if col < len(head_cells) else ""
                    zones = zones_in(cells_row[0]) or zones_in(line)
                    years = years_in(head) or years_in(head_cells[0]) or years_in(line)
                    ytd = (
                        "Jan to" in head
                        or "window" in head
                        or "Jan to" in head_cells[0]
                    ) or None
                else:
                    zones, years = zones_in(line), years_in(line)
                    ytd = (
                        "1 Jan to" in line
                        or "same dates" in line
                        or "same window" in line
                    ) or None
                target = hint_for(head, section) if ctx else None
                hits = candidates(cells, number, zones, years, ytd, section, target)
                if not ctx:
                    # Prose: accept a match only when the line names its zone and year and the
                    # number is not a small count; anything else needs a reviewed entry.
                    small = re.fullmatch(r"[+\u2212-]?\d{1,2}", number) is not None
                    hits = [
                        c
                        for c in hits
                        if not small
                        and c["key"].get("zone") in zones
                        and int(
                            c["key"].get("local_year", c["key"].get("year", 0)) or 0
                        )
                        in years
                    ]
                if not hits:
                    unmatched.append(f"{rel} | {number} | {line[:150]}")
                    continue
                c = hits[0]
                rows.append(
                    {
                        "doc": rel,
                        "quote": line,
                        "table": c["table"],
                        "where": where(c["key"]),
                        "expr": c["expr"],
                        "fmt": c["fmt"],
                        "agg": "",
                        "position": pos + 1,
                    }
                )
    if unmatched:
        print(f"{len(unmatched)} numbers not matched:")
        print("\n".join(unmatched))
    return rows


def main() -> None:
    snapshot = Path(__file__).resolve().parent / sys.argv[1]
    sys.path.insert(0, str(snapshot))
    from manual_numbers import MANUAL

    rows = build(snapshot, MANUAL)
    with (snapshot / "quoted_numbers.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "doc",
                "quote",
                "table",
                "where",
                "expr",
                "fmt",
                "agg",
                "position",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows")


if __name__ == "__main__":
    main()
