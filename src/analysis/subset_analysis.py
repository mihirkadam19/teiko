"""Part 4  Data Subset Analysis.

Baseline (time_from_treatment_start == 0) melanoma / miraclib / PBMC subset and
its breakdowns.

    python -m src.analysis.subset_analysis
        -> output/part4_baseline_subset.csv
        -> output/part4_baseline_summary.txt
"""

import sqlite3

import pandas as pd

from src.helpers import BaselineSubset
from src.paths import (
    BASELINE_SUBSET_PATH,
    BASELINE_SUMMARY_PATH,
    DB_PATH,
    ensure_output_dir,
)


def summarize_baseline_subset(df: pd.DataFrame) -> dict:
    """Three independent breakdowns of the baseline subset.

      1. by_project : sample count per project_id
      2. by_response: distinct subject count per response value
      3. by_sex     : distinct subject count per sex value
    """
    by_project = df.groupby("project_id").size()
    by_response = df.groupby("response")["subject_id"].nunique()
    by_sex = df.groupby("sex")["subject_id"].nunique()

    # Sanity check to make sure the joins are correct
    total_subjects = df["subject_id"].nunique()
    assert by_response.sum() == total_subjects, "response groups miscount subjects"
    assert by_sex.sum() == total_subjects, "sex groups miscount subjects"

    return {"by_project": by_project, "by_response": by_response, "by_sex": by_sex}


def format_baseline_summary(summary: dict) -> str:
    """Render the three breakdowns as clearly-labeled plain text."""
    sections = [
        ("Samples per project", summary["by_project"]),
        ("Distinct subjects by response", summary["by_response"]),
        ("Distinct subjects by sex", summary["by_sex"]),
    ]
    lines = ["=== Part 4: Baseline melanoma / PBMC / miraclib samples ==="]
    for title, series in sections:
        lines.append(f"\n{title}:")
        for key, value in series.items():
            lines.append(f"  {key:<10} {int(value)}")
    return "\n".join(lines)


def run_subset_analysis():
    """Generate the Part 4 baseline subset CSV and summary text."""
    ensure_output_dir()

    with sqlite3.connect(DB_PATH) as conn:
        subset = BaselineSubset().run(conn)

    summary = summarize_baseline_subset(subset)
    text = format_baseline_summary(summary)
    print(f"\n{text}\n")

    subset.to_csv(BASELINE_SUBSET_PATH, index=False)
    with open(BASELINE_SUMMARY_PATH, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")

    print(f"Wrote {BASELINE_SUBSET_PATH}  ({len(subset)} rows)")
    print(f"Wrote {BASELINE_SUMMARY_PATH}")


if __name__ == "__main__":
    run_subset_analysis()
