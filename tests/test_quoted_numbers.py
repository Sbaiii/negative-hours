"""Every number written in the README, finding notes and exec memo matches a frozen snapshot.

The live CSVs change every day, so prose quotes numbers from a frozen copy,
analysis/outputs/snapshots/<as-of date>/. Each snapshot has a quoted_numbers.csv
registry: one row per number quoted in a document, with the text around it (the
quote), where the number is in that text, and how to recompute it from the
snapshot (table, row filter, formula, format). Numbers that are not data values
(a constant such as "1 MW", a figure from an external source) are registered too,
with table "none" and the reason in `expr`.

Checks:
- every registered quote is in its document, and the recomputed value appears in
  it as a whole token with exactly that formatting (10.92 does not match −10.92 or
  110.92);
- if the value appears more than once in the quote, the registry must give its
  position (the n-th number in the quote), and the number there must match;
- every number in those documents is covered by a registered quote, so a new
  number can't be added to the prose without a check.
"""

import csv
import re
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS = REPO_ROOT / "analysis" / "outputs" / "snapshots"
DOCS = [
    REPO_ROOT / "README.md",
    *sorted((REPO_ROOT / "control-room" / "06 Findings").glob("*.md")),
    *sorted((REPO_ROOT / "docs").glob("*memo*.md")),
]
MINUS = "−"
REGISTRIES = sorted(SNAPSHOTS.glob("*/quoted_numbers.csv"))

# A number token: optional sign, digits with thousands separators, optional decimals.
TOKEN = re.compile(
    r"(?<![\w.,])[" + MINUS + r"+\-]?\d(?:[\d,]*\d)?(?:\.\d+)?(?!\d)(?!\.\d)(?!,\d)"
)


def registry_rows() -> list[dict]:
    rows = []
    for path in REGISTRIES:
        with path.open(encoding="utf-8") as f:
            rows += [{**row, "snapshot": path.parent} for row in csv.DictReader(f)]
    return rows


def select(snapshot: Path, table: str, where: str) -> pd.DataFrame:
    df = pd.read_csv(snapshot / f"{table}.csv")
    for condition in filter(None, where.split(";")):
        column, values = condition.split("=")
        df = df[df[column].astype(str).isin(values.split("|"))]
    assert len(df), f"{table} has no row for {where}"
    return df


def expected_text(row: dict) -> str:
    df = select(row["snapshot"], row["table"], row["where"])
    # expr is a formula from our own registry (e.g. "negative_hours / covered_hours * 100").
    values = df.apply(lambda r: eval(row["expr"], {}, r.to_dict()), axis=1)
    agg = row["agg"] or "one"
    if agg == "one":
        assert len(values) == 1, f"{row['where']} matches {len(values)} rows"
        value = float(values.iloc[0])
    elif agg in (
        "diff",
        "ratio",
        "pct_change",
    ):  # later vs earlier row (by year, then battery size)
        assert len(values) == 2, f"{row['where']} must match 2 rows for {agg}"
        keys = [k for k in ("local_year", "battery_duration_h") if k in df.columns]
        order = df.reset_index(drop=True).sort_values(keys).index.to_numpy()
        first, last = float(values.iloc[order[0]]), float(values.iloc[order[1]])
        value = {
            "diff": last - first,
            "ratio": last / first,
            "pct_change": (last / first - 1) * 100,
        }[agg]
    else:
        value = float(getattr(values, agg)())
    fmt = row["fmt"]
    if fmt.startswith("num"):  # like the docs: thousands separator, no trailing zeros
        decimals = int(fmt[3:] or 2)
        text = f"{value:,.{decimals}f}"
        if decimals:
            text = text.rstrip("0").rstrip(".")
    else:  # a format spec, e.g. ".1f", ",.0f", "+.1f" (signed)
        text = format(value, fmt)
    return text.replace("-", MINUS) if text.startswith("-") else text


def tokens(text: str) -> list[str]:
    return [t.replace("-", MINUS) for t in TOKEN.findall(text)]


def same(a: str, b: str) -> bool:
    """Equal as written, ignoring a leading plus sign."""
    return a.lstrip("+") == b.lstrip("+")


@pytest.mark.parametrize(
    "row", registry_rows(), ids=lambda r: f"{Path(r['doc']).name}: {r['quote'][:40]}"
)
def test_quoted_number_matches_snapshot(row):
    doc = (REPO_ROOT / row["doc"]).read_text(encoding="utf-8")
    assert row["quote"] in doc, f"quote not found in {row['doc']}: {row['quote']!r}"
    if row["table"] == "none":
        return  # not a data value; the reason is in expr
    expected = expected_text(row)
    found = tokens(row["quote"])
    if row["position"]:
        k = int(row["position"])
        assert k <= len(found), f"{row['quote']!r} has only {len(found)} numbers"
        assert same(found[k - 1], expected), (
            f"{row['doc']}: number {k} in {row['quote']!r} is {found[k - 1]!r}, expected {expected!r} "
            f"({row['table']} {row['where']} {row['expr']})"
        )
    else:
        hits = [t for t in found if same(t, expected)]
        assert len(hits) == 1, (
            f"{row['doc']}: {expected!r} appears {len(hits)} times as a whole number in {row['quote']!r} "
            f"(set its position if it appears more than once) ({row['table']} {row['where']} {row['expr']})"
        )


# Text with digits that are not quoted numbers.
NOT_NUMBERS = [
    r"`[^`]*`",  # code and file paths
    r"\[\[[^\]]*\]\]",  # wiki links
    r"\]\([^)]*\)",  # markdown link targets
    r"!\[[^\]]*\]",  # image alt text (it repeats a chart title)
    r"https?://\S+",
    r"<[^>]+>",  # HTML tags
    r"\b\d{4}-\d{2}-\d{2}\b",  # ISO dates
    r"\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b",  # 2 Oct
    r"\b\d{1,2}:\d{2}\b",  # clock times
    r"\b[A-Z]{2,}(?:-[A-Z0-9]+)+\b",  # identifiers (BOE-A-2022-9435)
    r"\b\d+/\d{4}\b",  # document numbers (605/2015), before years
    r"\b(?:19|20)\d\d\b",  # years
    r"\bQ\d(?:-\d)?\b",  # question and note ids
    r"\bADR-\d+\b",
    r"\bn\. \d+",  # rule numbers (DTF n. 12)
    r"\b\d+-min(?:ute)?\b",
    r"\b\d+-hour\b",
    r"\bchart \d[a-z]?\b",
    r"\bhttps?\b",
    # Thresholds and constants of the method (ADR-005 to ADR-008), not results.
    r"[<≤=>]\s*0\b(?![.,]\d)",
    r"\b(?:below|above|exactly|at|of|than) 0\b(?![.,]\d)",
    r"\b0 €/MWh",
    r"[−-]500 €/MWh",
    r"\b1 MW\b",
    r"\b[124] MWh\b",
    r"\b[124] h\b",
    r"\b[124] h battery\b|\b[124]-hour\b|\b[124] hours?\b",
    r"\b88% round trip\b",
    r"\b1(?:\.5)? (?:full )?cycles? a day\b",
    r"\b10 kWh\b",
    r"\b7 kW\b",
    r"\b(?:of the|of|all|in all) 8\b",
    r"\b8 (?:bidding )?zones\b",
]


def numbers_in(text: str) -> list[str]:
    for pattern in NOT_NUMBERS:
        text = re.sub(pattern, " ", text)
    return tokens(text)


@pytest.mark.parametrize("doc_path", DOCS, ids=lambda p: p.name)
def test_every_number_is_registered(doc_path):
    rel = doc_path.relative_to(REPO_ROOT).as_posix()
    quotes = [r["quote"] for r in registry_rows() if r["doc"] == rel]
    missing = []
    for line in doc_path.read_text(encoding="utf-8").split("\n"):
        if line.startswith("**Question:**"):
            continue  # note metadata (dates)
        for number in numbers_in(line):
            covered = any(q in line and number in tokens(q) for q in quotes)
            if not covered:
                missing.append(f"{number!r} in: {line[:140]}")
    assert not missing, (
        f"{len(missing)} numbers without a registered quote:\n" + "\n".join(missing)
    )
