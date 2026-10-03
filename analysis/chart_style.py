"""Shared chart style for the analysis notebooks: one colour per zone, everywhere.

Colours are the 8 categorical slots of a validated colour-blind-safe palette.
Which zone gets which slot is fixed (never by rank), so a zone keeps its colour
across every chart. Identity is never carried by colour alone: every chart also
names the zones in text (panel titles, axis labels or point labels).
"""

from pathlib import Path

import matplotlib as mpl

REPO_ROOT = Path(__file__).resolve().parent.parent
WAREHOUSE = REPO_ROOT / "data" / "warehouse.duckdb"
FIGURES = REPO_ROOT / "docs" / "figures"

# Zone -> colour. DE_LU, ES, NL and FR (often plotted close together) get the four
# slots that stay distinct for colour-blind readers even when every pair is compared.
ZONE_COLORS = {
    "DE_LU": "#2a78d6",  # blue
    "ES": "#eb6834",  # orange
    "NL": "#1baf7a",  # aqua
    "FR": "#4a3aa7",  # violet
    "BE": "#e87ba4",  # magenta
    "PT": "#eda100",  # yellow
    "PL": "#008300",  # green
    "IT_NORD": "#e34948",  # red
}

ZONE_LABELS = {
    "DE_LU": "Germany-Lux.",
    "ES": "Spain",
    "NL": "Netherlands",
    "FR": "France",
    "BE": "Belgium",
    "PT": "Portugal",
    "PL": "Poland",
    "IT_NORD": "North Italy",
}

# Chart chrome (light surface).
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
HIGHLIGHT_BAND = "#f0efec"

SOURCE = "Data: ENTSO-E Transparency Platform"


def apply_style() -> None:
    """Recessive axes and grid, system sans, light surface."""
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
            "font.size": 10,
            "text.color": INK,
            "axes.facecolor": SURFACE,
            "figure.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "axes.edgecolor": AXIS,
            "axes.labelcolor": INK_SECONDARY,
            "axes.titlecolor": INK,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 1,
            "xtick.color": INK_MUTED,
            "ytick.color": INK_MUTED,
            "xtick.labelcolor": INK_SECONDARY,
            "ytick.labelcolor": INK_SECONDARY,
            "ytick.left": False,
            "lines.linewidth": 2,
            "svg.fonttype": "path",  # text as outlines: the SVG looks the same everywhere
            "svg.hashsalt": "negative-hours",  # stable element ids: re-runs give identical SVGs
        }
    )


def add_title(fig, title: str, subtitle: str | None = None) -> None:
    """Title states the takeaway; subtitle says what is plotted."""
    fig.text(
        0.01, 0.985, title, ha="left", va="top", fontsize=14, weight="bold", color=INK
    )
    if subtitle:
        fig.text(
            0.01,
            0.935,
            subtitle,
            ha="left",
            va="top",
            fontsize=10.5,
            color=INK_SECONDARY,
        )


def add_source(fig, note: str | None = None) -> None:
    text = SOURCE if not note else f"{SOURCE}. {note}"
    fig.text(0.01, 0.012, text, ha="left", va="bottom", fontsize=8.5, color=INK_MUTED)


def save(fig, name: str) -> list[Path]:
    """Write docs/figures/<name>.svg and .png; return the paths."""
    FIGURES.mkdir(parents=True, exist_ok=True)
    paths = [FIGURES / f"{name}.svg", FIGURES / f"{name}.png"]
    fig.savefig(paths[0], metadata={"Date": None})  # no timestamp: identical on re-run
    fig.savefig(paths[1], dpi=200)
    return paths
