"""Frame conversion at the engine boundary.

Ubunye 0.7's pandas backend hands tasks Arrow-backed frames (pd.ArrowDtype),
so nullable integers stay integers exactly as on Spark. The analytics in this
package were written for classic numpy-backed pandas (np.select, np.where and
friends reject Arrow booleans), so tasks convert once, on the way in, to the
same dtypes plain ``pd.read_parquet`` would give.
"""

from __future__ import annotations

import pandas as pd
import pyarrow as pa


def _column(s: pd.Series) -> pd.Series:
    t = s.dtype
    if not isinstance(t, pd.ArrowDtype):
        return s
    at = t.pyarrow_dtype
    has_nulls = bool(s.isna().any())
    if pa.types.is_string(at) or pa.types.is_large_string(at):
        return s.astype("str")
    if pa.types.is_integer(at):
        return s.astype("float64") if has_nulls else s.astype(at.to_pandas_dtype())
    if pa.types.is_floating(at):
        return s.astype("float64")
    if pa.types.is_boolean(at):
        return s.astype(object).where(s.notna(), None) if has_nulls else s.astype(bool)
    if pa.types.is_timestamp(at):
        return pd.to_datetime(s.astype(object))
    if pa.types.is_date(at):
        return s.astype(object)  # python dates, as pd.read_parquet gives
    return s.astype(object)


def numpy_backed(df: pd.DataFrame) -> pd.DataFrame:
    """The same data with the numpy dtypes pd.read_parquet gives."""
    if not any(isinstance(t, pd.ArrowDtype) for t in df.dtypes):
        return df
    return pd.DataFrame({c: _column(df[c]) for c in df.columns}, index=df.index)


def all_numpy_backed(sources: dict) -> dict[str, pd.DataFrame]:
    return {name: numpy_backed(frame) for name, frame in sources.items()}
