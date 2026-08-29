"""Database query helpers

Every helper runs SQL against an open sqlite3 connection and returns the result
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class QueryHelper(ABC):
    """Base class for query helpers. Subclasses implement _fetch ."""

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


class FrequencyTable(QueryHelper):
    """Part 2 per sample relative frequency of each cell population.

    Columns: sample, total_count, population, count, percentage.
    One row per (sample, cell type); every sample in CellCount is included.
    """

    def _fetch(self, conn) -> pd.DataFrame:
        df = pd.read_sql(
            """
            SELECT sample_id AS sample,
                   cell_type AS population,
                   count
            FROM CellCount
            """,
            conn,
        )
        df["total_count"] = df.groupby("sample")["count"].transform("sum")
        df["percentage"] = (df["count"] / df["total_count"] * 100).round(2)
        return df[["sample", "total_count", "population", "count", "percentage"]]



