"""Part 2  Data Overview.

Writes the per sample cell population frequency table to disk.

    python -m src.analysis.freq_analysis    # -> output/part2_frequency_table.csv
"""

import sqlite3

from src.helpers import FrequencyTable
from src.paths import DB_PATH, FREQUENCY_TABLE_PATH, ensure_output_dir


def run_analysis():
    """Generate output/part2_frequency_table.csv from the SQLite database."""
    ensure_output_dir()

    with sqlite3.connect(DB_PATH) as conn:
        freq = FrequencyTable().run(conn)

    freq.to_csv(FREQUENCY_TABLE_PATH, index=False)

    n_samples = freq["sample"].nunique()
    print(f"Wrote {FREQUENCY_TABLE_PATH}")
    print(f"  {len(freq)} rows ({n_samples} samples)")


if __name__ == "__main__":
    run_analysis()