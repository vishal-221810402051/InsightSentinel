from __future__ import annotations

import json
import re
from typing import Any, List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models import ColumnStatistics, Dataset, DatasetColumn
from app.models.dataset_insight import DatasetInsight
from app.models.dataset_preview import DatasetPreview

_NUM_RE = re.compile(r"^[\s\+\-]?(?:\d+\.?\d*|\.\d+)(?:[eE][\+\-]?\d+)?\s*$")


def _canonical_row(r: dict) -> str:
    # stable JSON string for hashing
    return json.dumps(r, sort_keys=True, default=str, ensure_ascii=False)


def _to_float_like(v: Any) -> Optional[float]:
    """
    Try to parse a value into float in a tolerant way:
    - supports "1,234.56" (commas removed)
    - supports "\u20ac123" / "$123" (currency stripped)
    - rejects empty/None
    """
    if v is None:
        return None

    # Already numeric
    if isinstance(v, (int, float)) and not (isinstance(v, float) and (v != v)):  # NaN check
        return float(v)

    s = str(v).strip()
    if not s:
        return None

    # Remove common currency/percent symbols and spaces
    s = s.replace(",", "")
    s = s.replace("%", "")
    s = s.replace("\u20ac", "").replace("$", "").replace("\u00a3", "")

    if not _NUM_RE.match(s):
        return None

    try:
        f = float(s)
        # reject NaN/inf
        if f != f or f == float("inf") or f == float("-inf"):
            return None
        return f
    except Exception:
        return None


def _is_date_like_name(name: str) -> bool:
    n = (name or "").strip().lower()
    return any(k in n for k in ["date", "time", "timestamp", "datetime"])


def _is_categorical_dtype(dtype: str) -> bool:
    d = (dtype or "").lower()
    # SQLAlchemy stored dtype from pandas: "object", "bool", etc.
    # Also handle DB types you might store later: "varchar", "text", "char"
    return any(k in d for k in ["object", "bool", "category", "string", "varchar", "text", "char"])


def refresh_insights(db: Session, dataset_id) -> list[DatasetInsight]:
    dataset = (
        db.query(Dataset)
        .options(joinedload(Dataset.columns).joinedload(DatasetColumn.statistics))
        .filter(Dataset.id == dataset_id)
        .first()
    )
    if not dataset:
        return []

    preview = (
        db.query(DatasetPreview)
        .filter(DatasetPreview.dataset_id == dataset_id)
        .first()
    )
    preview_rows = preview.rows if preview else []

    insights: List[DatasetInsight] = []

    # clear old insights (idempotent refresh)
    db.query(DatasetInsight).filter(DatasetInsight.dataset_id == dataset_id).delete()

    # --- DUPLICATE_ROWS_IN_PREVIEW (dataset-level) ---
    if preview and preview.rows:
        seen = set()
        dup = 0
        for r in preview.rows:
            key = _canonical_row(r)
            if key in seen:
                dup += 1
            else:
                seen.add(key)

        if dup > 0:
            insights.append(
                DatasetInsight(
                    dataset_id=dataset.id,
                    column_id=None,  # dataset-level insight
                    severity="warning" if dup >= 1 else "info",
                    code="DUPLICATE_ROWS_IN_PREVIEW",
                    title="Duplicate rows detected (preview)",
                    message=f"Found {dup} duplicate row(s) in the first {len(preview.rows)} preview rows. Consider de-duplication rules.",
                )
            )

    if not preview or not preview.rows:
        insights.append(
            DatasetInsight(
                dataset_id=dataset.id,
                column_id=None,
                severity="warning",
                code="EMPTY_PREVIEW",
                title="No preview available",
                message="No preview rows were found for this dataset. Preview-based checks were skipped.",
            )
        )

    row_count = max(int(dataset.row_count or 0), 0)
    for col in dataset.columns:
        # --- HIGH_NULL_RATIO ---
        if row_count > 0:
            null_ratio = (col.null_count or 0) / row_count
            if null_ratio >= 0.2:
                severity = "critical" if null_ratio >= 0.5 else "warning"
                insights.append(
                    DatasetInsight(
                        dataset_id=dataset.id,
                        column_id=col.id,
                        severity=severity,
                        code="HIGH_NULL_RATIO",
                        title="High missing values",
                        message=f"Column '{col.name}' has {col.null_count}/{row_count} nulls ({null_ratio:.0%}). Consider imputation or dropping.",
                    )
                )

        # --- CONSTANT_COLUMN ---
        if row_count > 0 and (col.distinct_count or 0) <= 1:
            insights.append(
                DatasetInsight(
                    dataset_id=dataset.id,
                    column_id=col.id,
                    severity="warning",
                    code="CONSTANT_COLUMN",
                    title="Constant column",
                    message=f"Column '{col.name}' is constant (distinct={col.distinct_count}). Consider dropping.",
                )
            )

        numeric_as_string_detected = False

        # --- POTENTIAL_NUMERIC_AS_STRING (type integrity) ---
        # Use preview rows to see if values are mostly numeric but stored as object/string.
        if preview_rows and _is_categorical_dtype(col.dtype) and not _is_date_like_name(col.name):
            vals = []
            for r in preview_rows:
                if isinstance(r, dict) and col.name in r:
                    vals.append(r.get(col.name))

            non_null = [v for v in vals if v is not None and str(v).strip() != ""]

            # Noise gate: need enough evidence (small datasets should still work)
            if len(non_null) >= 3:
                parsed = [_to_float_like(v) for v in non_null]
                ok = [p for p in parsed if p is not None]
                ratio = len(ok) / len(non_null) if non_null else 0.0

                if ratio >= 0.80:
                    numeric_as_string_detected = True
                    insights.append(
                        DatasetInsight(
                            dataset_id=dataset.id,
                            column_id=col.id,
                            severity="warning",
                            code="POTENTIAL_NUMERIC_AS_STRING",
                            title="Numeric values stored as text",
                            message=(
                                f"Column '{col.name}' is stored as '{col.dtype}' but "
                                f"{len(ok)}/{len(non_null)} preview values ({ratio:.0%}) parse as numbers. "
                                "Consider casting/cleaning (remove separators/currency) to enable numeric analytics."
                            ),
                        )
                    )

        # --- LOW_CARDINALITY ---
        # Only add this if the column is NOT likely numeric-as-string (otherwise it's misleading)
        if row_count > 0 and not numeric_as_string_detected:
            dc = int(col.distinct_count or 0)
            if (
                _is_categorical_dtype(col.dtype)
                and not _is_date_like_name(col.name)
                and 1 < dc <= 5
            ):
                insights.append(
                    DatasetInsight(
                        dataset_id=dataset.id,
                        column_id=col.id,
                        severity="info",
                        code="LOW_CARDINALITY",
                        title="Low cardinality",
                        message=f"Column '{col.name}' has low cardinality ({dc} distinct). Treat as categorical/encode.",
                    )
                )

        # --- Stats-based rules (needs ColumnStatistics) ---
        st: ColumnStatistics | None = getattr(col, "statistics", None)
        if st:
            # OUTLIERS_DETECTED
            if st.outlier_ratio is not None and st.outlier_ratio >= 0.05:
                severity = "critical" if st.outlier_ratio >= 0.2 else "warning"
                oc = st.outlier_count if st.outlier_count is not None else 0
                insights.append(
                    DatasetInsight(
                        dataset_id=dataset.id,
                        column_id=col.id,
                        severity=severity,
                        code="OUTLIERS_DETECTED",
                        title="Outliers detected",
                        message=f"Column '{col.name}' has {oc} outliers ({st.outlier_ratio:.0%}). Investigate distribution / data errors.",
                    )
                )

            # NUMERIC_RANGE_SUSPICIOUS
            if st.min is not None and st.max is not None:
                if st.min == st.max:
                    insights.append(
                        DatasetInsight(
                            dataset_id=dataset.id,
                            column_id=col.id,
                            severity="info",
                            code="NUMERIC_RANGE_SUSPICIOUS",
                            title="Zero numeric range",
                            message=f"Column '{col.name}' has min==max ({st.min}). It may be constant or incorrectly parsed.",
                        )
                    )
                elif st.max <= 0 and st.min < 0:
                    insights.append(
                        DatasetInsight(
                            dataset_id=dataset.id,
                            column_id=col.id,
                            severity="warning",
                            code="NUMERIC_RANGE_SUSPICIOUS",
                            title="All values non-positive",
                            message=f"Column '{col.name}' appears fully non-positive (min={st.min}, max={st.max}). Validate domain assumptions.",
                        )
                    )

    # persist
    for i in insights:
        db.add(i)
    db.commit()

    return insights
