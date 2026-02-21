from __future__ import annotations

import pandas as pd


def profile_dataframe(df: pd.DataFrame) -> dict:
    """
    Returns:
      {
        "row_count": int,
        "column_count": int,
        "columns": [
            {"name": str, "dtype": str, "null_count": int, "distinct_count": int},
            ...
        ]
      }
    """
    row_count = int(df.shape[0])
    column_count = int(df.shape[1])

    cols = []
    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())
        # nunique(dropna=True) ignores NaN by default
        distinct_count = int(series.nunique(dropna=True))
        cols.append(
            {
                "name": str(col),
                "dtype": str(series.dtype),
                "null_count": null_count,
                "distinct_count": distinct_count,
            }
        )

    return {
        "row_count": row_count,
        "column_count": column_count,
        "columns": cols,
    }