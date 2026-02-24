from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.alert_rule import AlertRule
from app.models.column_statistics import ColumnStatistics
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_insight import DatasetInsight


def _canon_config(cfg: dict[str, Any]) -> str:
    # stable canonical representation for dedupe
    return json.dumps(cfg or {}, sort_keys=True, ensure_ascii=False, default=str)


@dataclass
class Suggestion:
    rule_type: str
    name: str
    description: str
    config: dict[str, Any]
    severity: str
    rationale: str


def build_alert_suggestions(db: Session, dataset_id, limit: int = 10) -> list[Suggestion]:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        return []

    # Existing rules for dedupe
    existing = (
        db.query(AlertRule)
        .filter(AlertRule.dataset_id == dataset_id)
        .all()
    )
    existing_keys = set()
    for r in existing:
        cfg = r.config if isinstance(r.config, dict) else {}
        existing_keys.add((r.rule_type, _canon_config(cfg)))

    # Pull columns + stats
    columns = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).all()
    cols_by_id = {str(c.id): c for c in columns}
    cols_by_name = {c.name: c for c in columns}

    stats = (
        db.query(ColumnStatistics)
        .join(DatasetColumn, DatasetColumn.id == ColumnStatistics.column_id)
        .filter(DatasetColumn.dataset_id == dataset_id)
        .all()
    )
    stats_by_col_id = {str(s.column_id): s for s in stats}

    # Pull insights
    insights = (
        db.query(DatasetInsight)
        .filter(DatasetInsight.dataset_id == dataset_id)
        .all()
    )
    insight_codes = {i.code for i in insights}
    insight_by_code = {}
    for i in insights:
        # keep one exemplar per code (enough for rationale)
        insight_by_code.setdefault(i.code, i)

    suggestions: list[Suggestion] = []

    def _add(s: Suggestion):
        key = (s.rule_type, _canon_config(s.config))
        if key in existing_keys:
            return
        if len(suggestions) >= max(1, min(int(limit), 50)):
            return
        suggestions.append(s)
        existing_keys.add(key)

    row_count = int(dataset.row_count or 0)

    # ----------------------------
    # High-signal proposals (not spam)
    # ----------------------------

    # A) OUTLIER_RATIO suggestions from stats
    for col_id, st in stats_by_col_id.items():
        if st.outlier_ratio is None:
            continue
        if st.outlier_ratio >= 0.05:
            col = cols_by_id.get(col_id)
            if not col:
                continue

            threshold = 0.05  # stable baseline
            _add(
                Suggestion(
                    rule_type="OUTLIER_RATIO",
                    name=f"Outlier ratio high: {col.name}",
                    description="Alert when outlier ratio indicates unusual distribution tail risk.",
                    config={"column": col.name, "op": ">=", "threshold": threshold},
                    severity="warning" if st.outlier_ratio < 0.20 else "critical",
                    rationale=(
                        f"ColumnStatistics.outlier_ratio={st.outlier_ratio:.2f} (>= 0.05). "
                        f"{'OUTLIERS_DETECTED insight present.' if 'OUTLIERS_DETECTED' in insight_codes else ''}"
                    ).strip(),
                )
            )

    # B) NULL_RATIO suggestions from column null_count
    for c in columns:
        if row_count <= 0:
            continue

        null_ratio = (c.null_count or 0) / row_count
        if null_ratio >= 0.20:
            _add(
                Suggestion(
                    rule_type="NULL_RATIO",
                    name=f"Missing values rising: {c.name}",
                    description="Alert when missing ratio suggests ingestion/data quality regression.",
                    config={"column": c.name, "op": ">=", "threshold": 0.20},
                    severity="warning" if null_ratio < 0.50 else "critical",
                    rationale=f"null_ratio={null_ratio:.0%} (>= 20%).",
                )
            )

    # C) Insight-based suggestions (ops-friendly)
    # These are great because they keep "rule logic" stable and let insights evolve.
    insight_targets = [
        ("SKEWED_DISTRIBUTION", "Skew detected (modeling risk)"),
        ("DATE_PARSE_FAILURE", "Date parse failures (time series broken)"),
        ("MIXED_DATE_FORMATS", "Mixed date formats (parsing ambiguity)"),
        ("FUTURE_DATES_IN_PREVIEW", "Future dates detected (timestamp correctness)"),
        ("LIKELY_IDENTIFIER", "Identifier-like column (aggregation risk)"),
        ("HIGH_CARDINALITY", "High cardinality (memory/joins risk)"),
    ]

    for code, label in insight_targets:
        if code in insight_codes:
            sev = "warning"
            ex = insight_by_code.get(code)
            # if an insight itself is info, still propose rule as info to avoid spam
            if ex and ex.severity in ("info",):
                sev = "info"

            _add(
                Suggestion(
                    rule_type="INSIGHT_PRESENT",
                    name=f"Data quality watch: {label}",
                    description="Alert when this insight appears (helps catch regressions).",
                    config={"code": code},
                    severity=sev,
                    rationale=f"Insight '{code}' exists for this dataset right now.",
                )
            )

    return suggestions
