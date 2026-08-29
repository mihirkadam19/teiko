"""Database query helpers.

Every helper runs SQL against an open sqlite3 connection and returns the
result - a pandas DataFrame, or a scalar for an aggregate query.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class QueryHelper(ABC):
    """Base class for query helpers. Subclasses implement `_fetch`."""

    def run(self, conn) -> pd.DataFrame:
        result = self._fetch(conn)
        if not isinstance(result, pd.DataFrame):
            raise TypeError(
                f"{type(self).__name__} must return a DataFrame, got {type(result).__name__}"
            )
        return result

    @abstractmethod
    def _fetch(self, conn) -> pd.DataFrame:
        raise NotImplementedError


    """Part 3 frequency table restricted to melanoma/miraclib/PBMC samples,
    with response ('yes'/'no') attached. One row per (sample, population)."""

    def _fetch(self, conn) -> pd.DataFrame:
        freq = FrequencyTable().run(conn)
        meta = pd.read_sql(
            """
            SELECT s.sample_id AS sample, e.response AS response
            FROM Sample s
            JOIN Enrollment e ON e.project_id = s.project_id
                             AND e.subject_id = s.subject_id
            WHERE e.condition = 'melanoma'
              AND e.treatment = 'miraclib'
              AND s.sample_type = 'PBMC'
              AND e.response IN ('yes', 'no')
            """,
            conn,
        )
        return freq.merge(meta, on="sample", how="inner")


    """Part 4 baseline melanoma/miraclib/PBMC samples.

    Columns: project_id, subject_id, sample_id, response, sex.
    One row per sample.
    """

    def _fetch(self, conn) -> pd.DataFrame:
        return pd.read_sql(
            """
            SELECT s.project_id AS project_id,
                   s.subject_id AS subject_id,
                   s.sample_id  AS sample_id,
                   e.response    AS response,
                   p.sex         AS sex
            FROM Sample s
            JOIN Enrollment e ON e.project_id = s.project_id
                             AND e.subject_id = s.subject_id
            JOIN Person p     ON p.subject_id = s.subject_id
            WHERE s.sample_type = 'PBMC'
              AND e.condition   = 'melanoma'
              AND e.treatment   = 'miraclib'
              AND s.time_from_treatment_start = 0
            """,
            conn,
        )


    """Bob's question: mean baseline b_cell count for melanoma male responders.

    Filters: condition == 'melanoma', sex == 'M', response == 'yes',
    time_from_treatment_start == 0. No filter on sample_type or treatment -
    every sample type and treatment arm is included.

    `run` returns a one-row DataFrame with a single `avg_bcell` column (the base
    class contract is DataFrame-in, DataFrame-out); use `value(conn)` for the
    rounded float.
    """

    def _fetch(self, conn) -> pd.DataFrame:
        return pd.read_sql(
            """
            SELECT AVG(cc.count) AS avg_bcell
            FROM Sample s
            JOIN Enrollment e ON e.project_id = s.project_id
                             AND e.subject_id = s.subject_id
            JOIN Person p     ON p.subject_id = s.subject_id
            JOIN CellCount cc ON cc.sample_id = s.sample_id
            WHERE e.condition = 'melanoma'
              AND p.sex       = 'M'
              AND e.response  = 'yes'
              AND s.time_from_treatment_start = 0
              AND cc.cell_type = 'b_cell'
            """,
            conn,
        )

    def value(self, conn) -> float:
        """The average b_cell count as a float rounded to 2 dp."""
        return round(float(self.run(conn)["avg_bcell"].iloc[0]), 2)