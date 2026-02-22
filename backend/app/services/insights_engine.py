from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any, List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models import ColumnStatistics, Dataset, DatasetColumn
from app.models.dataset_insight import DatasetInsight
from app.models.dataset_preview import DatasetPreview

_NUM_RE = re.compile(r"^[\s\+\-]?(?:\d+\.?\d*|\.\d+)(?:[eE][\+\-]?\d+)?\s*$")
_DATE_HINT_RE = re.compile(
    r"^\s*\d{4}-\d{2}-\d{2}(\s+\d{2}:\d{2}(:\d{2})?)?\s*$"  # 2026-01-02 or 2026-01-02 12:30(:45)
)
_EU_DATE_RE = re.compile(r"^\s*\d{2}/\d{2}/\d{4}\s*$")  # 31/12/2026
_US_DATE_RE = re.compile(r"^\s*\d{2}-\d{2}-\d{4}\s*$")  # 12-31-2026 (ambiguous but common)


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


def _date_family(v: Any) -> Optional[str]:
    """Classify a date-ish string into a format family to detect mixed formats."""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None

    # quick family detection (cheap, avoids heavy parsing)
    if _DATE_HINT_RE.match(s):
        return "ISO"
    if _EU_DATE_RE.match(s):
        return "EU_SLASH"
    if _US_DATE_RE.match(s):
        return "US_DASH"

    # fallback: try python parsing for common iso-ish shapes
    # Keep it conservative to avoid false positives
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return "ISO_LIKE"
    except Exception:
        return "UNKNOWN"


def _try_parse_datetime(v: Any) -> Optional[datetime]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None

    # normalize Z
    s2 = s.replace("Z", "+00:00")

    # Try ISO first
    try:
        dt = datetime.fromisoformat(s2)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass

    # Try EU slash dd/mm/yyyy
    try:
        dt = datetime.strptime(s, "%d/%m/%Y").replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    # Try US dash mm-dd-yyyy
    try:
        dt = datetime.strptime(s, "%m-%d-%Y").replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    return None


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
        n = len(preview.rows)

        # count duplicates using canonical representation
        seen = set()
        dup = 0
        for r in preview.rows:
            key = _canonical_row(r)
            if key in seen:
                dup += 1
            else:
                seen.add(key)

        if dup > 0 and n > 0:
            dup_ratio = dup / n

            # detect "constant dimensions" (columns that have exactly 1 distinct non-null value in preview)
            constant_cols = 0
            if isinstance(preview.rows[0], dict):
                keys = list(preview.rows[0].keys())
                for k in keys:
                    vals = []
                    for r in preview.rows:
                        if isinstance(r, dict):
                            v = r.get(k)
                            if v is not None and str(v).strip() != "":
                                vals.append(str(v))
                    if len(set(vals)) <= 1 and len(vals) > 0:
                        constant_cols += 1

            # severity decision
            if constant_cols >= 2:
                severity = "info"
                msg_extra = f"Duplicates may be expected because {constant_cols} column(s) appear constant in preview."
            else:
                if dup_ratio < 0.05:
                    severity = "info"
                else:
                    severity = "warning"
                msg_extra = "Consider de-duplication rules or upstream export logic."

            insights.append(
                DatasetInsight(
                    dataset_id=dataset.id,
                    column_id=None,
                    severity=severity,
                    code="DUPLICATE_ROWS_IN_PREVIEW",
                    title="Duplicate rows detected (preview)",
                    message=(
                        f"Found {dup} duplicate row(s) in the first {n} preview rows "
                        f"({dup_ratio:.0%}). {msg_extra}"
                    ),
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

        # --- HIGH_CARDINALITY (categorical blow-up / likely IDs) ---
        if row_count > 0 and _is_categorical_dtype(col.dtype) and not _is_date_like_name(col.name):
            dc = int(col.distinct_count or 0)
            distinct_ratio = (dc / row_count) if row_count else 0.0

            # gates to avoid spam on tiny datasets
            if row_count >= 50 and dc >= 50 and distinct_ratio >= 0.50:
                insights.append(
                    DatasetInsight(
                        dataset_id=dataset.id,
                        column_id=col.id,
                        severity="warning",
                        code="HIGH_CARDINALITY",
                        title="High cardinality categorical column",
                        message=(
                            f"Column '{col.name}' has high cardinality ({dc} distinct out of {row_count}, {distinct_ratio:.0%}). "
                            "This can break one-hot encoding and may indicate an identifier/free-text field. "
                            "Consider hashing, target encoding, grouping rare categories, or excluding from modeling."
                        ),
                    )
                )

            # even stronger signal: likely identifier
            if row_count >= 50 and dc >= 50 and distinct_ratio >= 0.95:
                insights.append(
                    DatasetInsight(
                        dataset_id=dataset.id,
                        column_id=col.id,
                        severity="warning",
                        code="LIKELY_IDENTIFIER",
                        title="Likely identifier column",
                        message=(
                            f"Column '{col.name}' looks like an identifier ({dc}/{row_count} distinct, {distinct_ratio:.0%}). "
                            "Identifiers should not be treated as features; use for joins only."
                        ),
                    )
                )

        # --- DATE/TIME QUALITY (preview-based) ---
        if preview_rows and _is_date_like_name(col.name):
            vals = []
            for r in preview_rows:
                if isinstance(r, dict) and col.name in r:
                    vals.append(r.get(col.name))

            non_null = [v for v in vals if v is not None and str(v).strip() != ""]
            if len(non_null) >= 5:
                parsed = [_try_parse_datetime(v) for v in non_null]
                ok = [p for p in parsed if p is not None]
                ratio = (len(ok) / len(non_null)) if non_null else 0.0

                # DATE_PARSE_FAILURE
                if ratio < 0.80:
                    insights.append(
                        DatasetInsight(
                            dataset_id=dataset.id,
                            column_id=col.id,
                            severity="warning",
                            code="DATE_PARSE_FAILURE",
                            title="Date/time parse failures",
                            message=(
                                f"Column '{col.name}' looks like a date/time field but only "
                                f"{len(ok)}/{len(non_null)} preview values ({ratio:.0%}) could be parsed. "
                                "Standardize formats (ISO 8601 recommended) and remove invalid values."
                            ),
                        )
                    )

                # MIXED_DATE_FORMATS (only if parse is mostly OK; avoids spam)
                families = {}
                for v in non_null:
                    fam = _date_family(v)
                    if fam and fam != "UNKNOWN":
                        families[fam] = families.get(fam, 0) + 1

                strong_families = {k: c for k, c in families.items() if c >= 2}
                if len(strong_families) >= 2 and ratio >= 0.80:
                    fams = ", ".join([f"{k}({c})" for k, c in sorted(strong_families.items(), key=lambda x: -x[1])])
                    insights.append(
                        DatasetInsight(
                            dataset_id=dataset.id,
                            column_id=col.id,
                            severity="warning",
                            code="MIXED_DATE_FORMATS",
                            title="Mixed date formats detected",
                            message=(
                                f"Column '{col.name}' contains mixed date/time formats in preview: {fams}. "
                                "Normalize to a single standard (ISO 8601) to avoid sorting/aggregation issues."
                            ),
                        )
                    )

                # FUTURE_DATES_IN_PREVIEW (optional but useful; keep as info to prevent spam)
                now = datetime.now(timezone.utc)
                future = [dt for dt in ok if dt and dt > (now.replace(microsecond=0))]
                # add a tolerance: ignore tiny future if time zones
                if future and ratio >= 0.80:
                    insights.append(
                        DatasetInsight(
                            dataset_id=dataset.id,
                            column_id=col.id,
                            severity="info",
                            code="FUTURE_DATES_IN_PREVIEW",
                            title="Future dates found (preview)",
                            message=(
                                f"Column '{col.name}' contains future date/time values in preview. "
                                "Confirm whether this is expected (e.g., scheduled events) or a parsing/timezone/data-entry issue."
                            ),
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

            # --- SKEWNESS (distribution shape) ---
            if st.skewness is not None and row_count >= 50:
                s = float(st.skewness)
                abs_s = abs(s)
                if abs_s >= 2.0:
                    sev = "warning"
                elif abs_s >= 1.0:
                    sev = "info"
                else:
                    sev = None

                if sev:
                    insights.append(
                        DatasetInsight(
                            dataset_id=dataset.id,
                            column_id=col.id,
                            severity=sev,
                            code="SKEWED_DISTRIBUTION",
                            title="Skewed distribution",
                            message=(
                                f"Column '{col.name}' is skewed (skewness={s:.2f}). "
                                "Consider log transform, winsorization, or robust statistics for alerts/modeling."
                            ),
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
