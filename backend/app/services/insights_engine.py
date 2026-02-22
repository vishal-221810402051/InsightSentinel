from __future__ import annotations

import json
from typing import List

from sqlalchemy.orm import Session, joinedload

from app.models import ColumnStatistics, Dataset, DatasetColumn
from app.models.dataset_insight import DatasetInsight
from app.models.dataset_preview import DatasetPreview


def _canonical_row(r: dict) -> str:
    # stable JSON string for hashing
    return json.dumps(r, sort_keys=True, default=str, ensure_ascii=False)


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

    insights: List[DatasetInsight] = []

    # clear old insights (idempotent refresh)
    db.query(DatasetInsight).filter(DatasetInsight.dataset_id == dataset_id).delete()

    # --- DUPLICATE_ROWS_IN_PREVIEW (dataset-level) ---
    preview = db.query(DatasetPreview).filter(DatasetPreview.dataset_id == dataset_id).first()
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

        # --- LOW_CARDINALITY ---
        if row_count > 0:
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
