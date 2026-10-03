"""Every 2026 number written in the README and finding notes matches a frozen snapshot.

2026 is not over, so the live CSVs change every day. Prose quotes 2026 numbers
"as of" a date instead, from analysis/outputs/snapshots/<date>/. Each snapshot has a
quoted_numbers.csv registry: one row per quoted number, saying which document
quotes it, the exact text around it, and how to recompute it from the snapshot.

Two checks:
- every registered quote is in its document and contains the recomputed value;
- every number on a line about 2026 (or in a table column headed 2026) in those
  documents is covered by a registered quote, so a new 2026 number can't be
  added without a check.
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
]
MINUS = "−"

REGISTRIES = sorted(SNAPSHOTS.glob("*/quoted_numbers.csv"))


def registry_rows() -> list[dict]:
    rows = []
    for path in REGISTRIES:
        with path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append({**row, "snapshot": path.parent})
    return rows


def select(snapshot: Path, table: str, where: str) -> pd.DataFrame:
    df = pd.read_csv(snapshot / f"{table}.csv")
    for condition in filter(None, where.split(";")):
        column, values = condition.split("=")
        allowed = values.split("|")
        df = df[df[column].astype(str).isin(allowed)]
    assert len(df), f"{table} has no row for {where}"
    return df


def expected_text(row: dict) -> str:
    df = select(row["snapshot"], row["table"], row["where"])
    # expr is a formula from our own registry (e.g. "negative_hours / covered_hours * 100").
    values = df.apply(lambda r: eval(row["expr"], {}, r.to_dict()), axis=1)
    agg = row["agg"] or "one"
    if agg == "one":
        assert len(values) == 1, f"{row['where']} matches {len(values)} rows"
        value = values.iloc[0]
    else:
        value = getattr(values, agg)()
    fmt = row["fmt"]
    if fmt.startswith("num"):  # like the docs: thousands separator, no trailing zeros
        decimals = int(fmt[3:] or 2)
        text = f"{float(value):,.{decimals}f}"
        return text.rstrip("0").rstrip(".") if decimals else text
    return format(float(value), fmt)


@pytest.mark.parametrize(
    "row", registry_rows(), ids=lambda r: f"{Path(r['doc']).name}: {r['quote'][:40]}"
)
def test_quoted_number_matches_snapshot(row):
    doc = (REPO_ROOT / row["doc"]).read_text(encoding="utf-8")
    assert row["quote"] in doc, f"quote not found in {row['doc']}: {row['quote']!r}"
    if row["table"] == "none":
        return  # a number that isn't a data value (declared with a reason)
    expected = expected_text(row)
    variants = {expected, expected.replace("-", MINUS)}
    assert any(v in row["quote"] for v in variants), (
        f"{row['doc']}: quote {row['quote']!r} should contain {expected!r} "
        f"({row['table']} {row['where']} {row['expr']})"
    )


# Text that contains digits but isn't a quoted number.
NOT_NUMBERS = [
    r"`[^`]*`",  # code and file paths
    r"\[\[[^\]]*\]\]",  # wiki links
    r"\]\([^)]*\)",  # markdown link targets
    r"https?://\S+",
    r"\b\d{4}-\d{2}-\d{2}\b",  # ISO dates
    r"\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b",  # 2 Oct
    r"\b\d{1,2}:\d{2}\b",  # clock times
    r"\b\d+/\d{4}\b",  # document numbers (605/2015), before years
    r"\b20[1-3]\d\b",  # years
    r"\bQ\d(?:-\d)?\b",
    r"\bADR-\d+\b",
    r"[<≤=>]\s*0\b",  # thresholds: < 0, ≤ 0
    r"\b(?:below|above|exactly|at|of) 0\b",
    r"[−-]?\d+ €/MWh\b",  # price rules (0 €/MWh, −500 €/MWh)
    r"\bn\. \d+",  # rule numbers (DTF n. 12)
    r"\b\d+-min(?:ute)?\b",
    r"\bchart \d\b",
]
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers_in(text: str) -> list[str]:
    for pattern in NOT_NUMBERS:
        text = re.sub(pattern, " ", text)
    return NUMBER.findall(text)


def lines_about_2026(doc: str) -> list[str]:
    """Lines mentioning 2026, plus the 2026 cells of tables with a 2026 column."""
    lines, out = doc.split("\n"), []
    i = 0
    while i < len(lines):
        line = lines[i]
        is_table = (
            line.startswith("|")
            and i + 1 < len(lines)
            and set(lines[i + 1]) <= set("|-: ")
        )
        if is_table:
            header = [c.strip() for c in line.strip("|").split("|")]
            whole = "2026" in header[0]
            cols = [k for k, c in enumerate(header) if whole or "2026" in c]
            i += 2  # the header itself names columns, it quotes no numbers
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip("|").split("|")]
                out.extend(cells[k] for k in cols if k < len(cells))
                i += 1
            continue
        if "2026" in numbers_free_of_links(line) and not line.startswith("!["):
            out.append(line)
        i += 1
    return out


def numbers_free_of_links(line: str) -> str:
    return re.sub(
        r"\[\[[^\]]*\]\]|\]\([^)]*\)|`[^`]*`|\b\d{4}-\d{2}-\d{2}\b", " ", line
    )


@pytest.mark.parametrize("doc_path", DOCS, ids=lambda p: p.name)
def test_every_2026_number_is_registered(doc_path):
    doc = doc_path.read_text(encoding="utf-8")
    rel = doc_path.relative_to(REPO_ROOT).as_posix()
    quotes = [r["quote"] for r in registry_rows() if r["doc"] == rel]
    missing = []
    for text in lines_about_2026(doc):
        for number in numbers_in(text):
            covered = any(number in q and (q in text or text in q) for q in quotes)
            if not covered:
                missing.append(f"{number!r} in: {text[:120]}")
    assert not missing, "2026 numbers without a registered quote:\n" + "\n".join(
        missing
    )
