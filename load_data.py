"""Part 1 - Data Management.

Initializes a SQLite database (`cell_counts.db`) in the repository root and
loads `cell-count.csv` into a normalized schema.

Run directly:

    python load_data.py

Re-running is safe: the tables are dropped and recreated on every run, so no
duplicate rows accumulate.
"""

import sqlite3

import pandas as pd

from src.paths import CSV_PATH, DB_PATH

CELL_TYPES = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

SCHEMA = """
DROP TABLE IF EXISTS CellCount;
DROP TABLE IF EXISTS Sample;
DROP TABLE IF EXISTS Enrollment;
DROP TABLE IF EXISTS Person;
DROP TABLE IF EXISTS Project;

CREATE TABLE Project (
    project_id TEXT PRIMARY KEY
);

CREATE TABLE Person (
    subject_id TEXT PRIMARY KEY,
    sex TEXT
);

CREATE TABLE Enrollment (
    project_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    condition TEXT,
    age INTEGER,
    treatment TEXT,
    response TEXT,
    PRIMARY KEY (project_id, subject_id),
    FOREIGN KEY (project_id) REFERENCES Project(project_id),
    FOREIGN KEY (subject_id) REFERENCES Person(subject_id)
);

CREATE TABLE Sample (
    sample_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    sample_type TEXT,
    time_from_treatment_start INTEGER,
    FOREIGN KEY (project_id, subject_id) REFERENCES Enrollment(project_id, subject_id)
);

CREATE TABLE CellCount (
    sample_id TEXT NOT NULL,
    cell_type TEXT NOT NULL,
    count INTEGER,
    PRIMARY KEY (sample_id, cell_type),
    FOREIGN KEY (sample_id) REFERENCES Sample(sample_id)
);
"""


def _nullable_int(value):
    """Convert a pandas value to a plain int, or None when missing."""
    if pd.isna(value):
        return None
    return int(value)


def init_db(conn):
    """Create the schema, dropping any existing tables first (idempotent)."""
    conn.executescript(SCHEMA)
    conn.commit()


def load_csv(conn):
    """Load every row of cell-count.csv into the schema created by init_db."""
    df = pd.read_csv(CSV_PATH, dtype=str)

    # Project: one row per distinct project value.
    projects = sorted(df["project"].dropna().unique())
    conn.executemany(
        "INSERT INTO Project (project_id) VALUES (?)",
        [(p,) for p in projects],
    )

    # Person: one row per distinct subject, with its sex.
    persons = (
        df[["subject", "sex"]]
        .drop_duplicates(subset="subject")
        .sort_values("subject")
    )
    conn.executemany(
        "INSERT INTO Person (subject_id, sex) VALUES (?, ?)",
        list(persons.itertuples(index=False, name=None)),
    )

    # Enrollment: one row per distinct (project, subject) pair.
    enrollments = (
        df[["project", "subject", "condition", "age", "treatment", "response"]]
        .drop_duplicates(subset=["project", "subject"])
        .sort_values(["project", "subject"])
    )
    conn.executemany(
        """INSERT INTO Enrollment
           (project_id, subject_id, condition, age, treatment, response)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [
            (r.project, r.subject, r.condition, _nullable_int(r.age),
             r.treatment, r.response)
            for r in enrollments.itertuples(index=False)
        ],
    )

    # Sample: one row per CSV row.
    samples = df[
        ["sample", "project", "subject", "sample_type", "time_from_treatment_start"]
    ]
    conn.executemany(
        """INSERT INTO Sample
           (sample_id, project_id, subject_id, sample_type, time_from_treatment_start)
           VALUES (?, ?, ?, ?, ?)""",
        [
            (r.sample, r.project, r.subject, r.sample_type,
             _nullable_int(r.time_from_treatment_start))
            for r in samples.itertuples(index=False)
        ],
    )

    # CellCount: 5 rows per CSV row, one per cell type.
    cell_rows = []
    for r in df.itertuples(index=False):
        for cell_type in CELL_TYPES:
            cell_rows.append(
                (r.sample, cell_type, _nullable_int(getattr(r, cell_type)))
            )
    conn.executemany(
        "INSERT INTO CellCount (sample_id, cell_type, count) VALUES (?, ?, ?)",
        cell_rows,
    )

    conn.commit()


def print_row_counts(conn):
    """Print per-table row counts for sanity check."""
    print(f"Loaded {CSV_PATH} -> {DB_PATH}")
    for table in ("Project", "Person", "Enrollment", "Sample", "CellCount"):
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<12} {n:>6} rows")


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        init_db(conn)
        load_csv(conn)
        print_row_counts(conn)
    except Exception as exc:
        print(f"Error creating schema: {exc}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
