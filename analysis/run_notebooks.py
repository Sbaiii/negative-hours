"""Re-run the analysis notebooks in place (charts are re-exported to docs/figures).

Run after the warehouse is built (from the repo root):
    uv run python analysis/run_notebooks.py            # all four
    uv run python analysis/run_notebooks.py q1 q3      # some of them
"""

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ANALYSIS = Path(__file__).resolve().parent


def run(path: Path) -> None:
    nb = nbformat.read(path, as_version=4)
    NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(ANALYSIS)}}).execute()
    nbformat.write(nb, path)
    print(f"ran {path.relative_to(ANALYSIS.parent)}")


def main() -> None:
    wanted = sys.argv[1:]
    for path in sorted(ANALYSIS.glob("q*_*.ipynb")):
        if not wanted or any(path.name.startswith(w) for w in wanted):
            run(path)


if __name__ == "__main__":
    main()
