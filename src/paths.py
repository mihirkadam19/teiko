"""Filesystem paths - single source of truth for the whole project.

Everything is resolved relative to this file (src/paths.py -> src/ -> repo root),
so the paths are correct regardless of the current working directory or how a
script is launched (`python load_data.py`, `python -m src.analysis.x`,
`streamlit run src/dashboard.py`).
"""

import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Inputs
CSV_PATH = os.path.join(REPO_ROOT, "cell-count.csv")
DB_PATH = os.path.join(REPO_ROOT, "cell_counts.db")

# Output directory
OUTPUT_DIR = os.path.join(REPO_ROOT, "output")

FREQUENCY_TABLE_PATH = os.path.join(OUTPUT_DIR, "part2_frequency_table.csv")

STATS_RESULTS_PATH = os.path.join(OUTPUT_DIR, "part3_stats_results.csv")
BOXPLOT_PATH = os.path.join(OUTPUT_DIR, "part3_boxplot.png")
RESPONDER_SUMMARY_PATH = os.path.join(OUTPUT_DIR, "part3_responder_summary.txt")



def ensure_output_dir() -> None:
    """Create the output directory if it doesn't already exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
