"""Part 4  Bob's question.

Considering melanoma males of ALL sample and treatment types, what is the
average number of B cells for responders at time_from_treatment_start == 0?

    python -m src.analysis.avg_bcell    # -> output/part4_avg_bcell.txt
"""

import sqlite3

from src.helpers import AverageBCell
from src.paths import AVG_BCELL_PATH, DB_PATH, ensure_output_dir


def run_avg_bcell():
    """Compute the average and write it to output/part4_avg_bcell.txt."""
    ensure_output_dir()

    with sqlite3.connect(DB_PATH) as conn:
        avg_bcell = AverageBCell().value(conn)

    line = (
        "Average B cells - melanoma males, responders, time=0, "
        f"all sample & treatment types: {avg_bcell:.2f}"
    )
    print(line)
    with open(AVG_BCELL_PATH, "w", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(f"Wrote {AVG_BCELL_PATH}")


if __name__ == "__main__":
    run_avg_bcell()
