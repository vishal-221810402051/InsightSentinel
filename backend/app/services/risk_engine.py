from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import Dataset, DatasetColumn, DatasetInsight
from app.models.alert_event import AlertEvent
from app.models.column_statistics import ColumnStatistics
from app.models.dataset_risk_history import DatasetRiskHistory

logger = logging.getLogger("insightsentinel.risk")


@dataclass
class RiskItem:
    kind: str  # INSIGHT | STAT | ALERT | STRUCT
    code: str
    weight: float
    detail: Dict[str, Any]


@dataclass
class RiskScoreResult:
    dataset_id: str
    dataset_risk_score: int
    risk_level: str
    breakdown: Dict[str, int]
    top_risks: List[Dict[str, Any]]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _risk_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 20:
        return "moderate"
    return "low"


# --- Configurable weights (V1) ---
INSIGHT_WEIGHTS: Dict[str, int] = {
    "HIGH_NULL_RATIO": 12,
    "OUTLIERS_DETECTED": 10,
    "DATE_PARSE_FAILURE": 10,
    "SKEWED_DISTRIBUTION": 8,
    "MIXED_DATE_FORMATS": 8,
    "FUTURE_DATES_IN_PREVIEW": 6,
    "HIGH_CARDINALITY": 6,
    "LIKELY_IDENTIFIER": 4,
    "NUMERIC_RANGE_SUSPICIOUS": 4,
    "POTENTIAL_NUMERIC_AS_STRING": 10,
    "DUPLICATE_ROWS_IN_PREVIEW": 4,  # low weight; often expected
    "CONSTANT_COLUMN": 3,
    "LOW_CARDINALITY": 1,  # informational
}

MAX_INSIGHT_SCORE = 40
MAX_STAT_SCORE = 30
MAX_ALERT_SCORE = 20
MAX_STRUCT_SCORE = 10

# --- Risk spike config ---
RISK_SPIKE_WARNING_THRESHOLD = 10
RISK_SPIKE_CRITICAL_THRESHOLD = 20
RISK_SPIKE_COOLDOWN_MINUTES = 60


def compute_dataset_risk(db: Session, dataset_id) -> Optional[RiskScoreResult]:
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        return None

    # --- Load signals ---
    insights = (
        db.query(DatasetInsight)
        .filter(DatasetInsight.dataset_id == dataset_id)
        .all()
    )

    columns = (
        db.query(DatasetColumn)
        .filter(DatasetColumn.dataset_id == dataset_id)
        .all()
    )
    cols_by_id = {str(c.id): c for c in columns}

    stats = (
        db.query(ColumnStatistics)
        .join(DatasetColumn, DatasetColumn.id == ColumnStatistics.column_id)
        .filter(DatasetColumn.dataset_id == dataset_id)
        .all()
    )
    stats_by_col_id = {str(s.column_id): s for s in stats}

    # Recent alerts (24h)
    cutoff = _now() - timedelta(hours=24)
    recent_alerts_count = (
        db.query(AlertEvent)
        .filter(AlertEvent.dataset_id == dataset_id)
        .filter(AlertEvent.created_at >= cutoff)
        .count()
    )

    row_count = int(ds.row_count or 0)

    # --- 1) Insight Risk ---
    insight_score = 0
    seen_codes = set()
    risk_items: List[RiskItem] = []

    for ins in insights:
        code = (ins.code or "").strip()
        if not code or code in seen_codes:
            continue

        seen_codes.add(code)
        w = int(INSIGHT_WEIGHTS.get(code, 2))
        insight_score += w

        risk_items.append(
            RiskItem(
                kind="INSIGHT",
                code=code,
                weight=w,
                detail={
                    "severity": ins.severity,
                    "title": ins.title,
                    "message": ins.message,
                    "column_id": str(ins.column_id) if ins.column_id else None,
                },
            )
        )

    insight_score = min(insight_score, MAX_INSIGHT_SCORE)

    # --- 2) Statistical Risk (uses ColumnStatistics) ---
    stat_score = 0
    for col_id, st in stats_by_col_id.items():
        col = cols_by_id.get(col_id)
        col_name = col.name if col else col_id

        # outlier_ratio bands
        if st.outlier_ratio is not None:
            if st.outlier_ratio >= 0.20:
                stat_score += 15
                risk_items.append(
                    RiskItem(
                        kind="STAT",
                        code="OUTLIER_RATIO_HIGH",
                        weight=15,
                        detail={"column": col_name, "outlier_ratio": float(st.outlier_ratio)},
                    )
                )
            elif st.outlier_ratio >= 0.05:
                stat_score += 8
                risk_items.append(
                    RiskItem(
                        kind="STAT",
                        code="OUTLIER_RATIO_ELEVATED",
                        weight=8,
                        detail={"column": col_name, "outlier_ratio": float(st.outlier_ratio)},
                    )
                )

        # skewness bands (5D-C uses your 6E-d fields)
        if st.skewness is not None:
            s = abs(float(st.skewness))
            if s >= 2.0:
                stat_score += 10
                risk_items.append(
                    RiskItem(
                        kind="STAT",
                        code="SKEWNESS_HIGH",
                        weight=10,
                        detail={"column": col_name, "skewness": float(st.skewness)},
                    )
                )
            elif s >= 1.0:
                stat_score += 5
                risk_items.append(
                    RiskItem(
                        kind="STAT",
                        code="SKEWNESS_ELEVATED",
                        weight=5,
                        detail={"column": col_name, "skewness": float(st.skewness)},
                    )
                )

    stat_score = min(stat_score, MAX_STAT_SCORE)

    # --- 3) Alert Pressure Risk ---
    if recent_alerts_count <= 0:
        alert_score = 0
    elif recent_alerts_count <= 2:
        alert_score = 5
    elif recent_alerts_count <= 5:
        alert_score = 10
    else:
        alert_score = 20

    if alert_score > 0:
        risk_items.append(
            RiskItem(
                kind="ALERT",
                code="RECENT_ALERT_PRESSURE",
                weight=alert_score,
                detail={"alerts_last_24h": int(recent_alerts_count)},
            )
        )

    # --- 4) Structural Risk ---
    # (a) many constant columns
    constant_cols = sum(1 for ins in insights if (ins.code or "") == "CONSTANT_COLUMN")
    struct_score = 0

    if constant_cols >= 2:
        struct_score += 5
        risk_items.append(
            RiskItem(
                kind="STRUCT",
                code="MANY_CONSTANT_COLUMNS",
                weight=5,
                detail={"constant_columns": int(constant_cols)},
            )
        )

    # (b) high-cardinality + low rows (fragility)
    has_high_card = any((ins.code or "") == "HIGH_CARDINALITY" for ins in insights)
    if has_high_card and row_count > 0 and row_count < 200:
        struct_score += 5
        risk_items.append(
            RiskItem(
                kind="STRUCT",
                code="HIGH_CARDINALITY_LOW_ROWS",
                weight=5,
                detail={"row_count": row_count},
            )
        )

    struct_score = min(struct_score, MAX_STRUCT_SCORE)

    # --- total ---
    total = insight_score + stat_score + alert_score + struct_score
    total = min(int(round(total)), 100)

    # top risks = highest weight first
    top = sorted(risk_items, key=lambda x: float(x.weight), reverse=True)[:10]
    top_risks = [
        {
            "kind": t.kind,
            "code": t.code,
            "weight": t.weight,
            "detail": t.detail,
        }
        for t in top
    ]

    return RiskScoreResult(
        dataset_id=str(dataset_id),
        dataset_risk_score=total,
        risk_level=_risk_level(total),
        breakdown={
            "insight_score": int(insight_score),
            "stat_score": int(stat_score),
            "alert_score": int(alert_score),
            "struct_score": int(struct_score),
        },
        top_risks=top_risks,
    )


def _risk_spike_cooldown_exists(db: Session, dataset_id) -> bool:
    cutoff = _now() - timedelta(minutes=RISK_SPIKE_COOLDOWN_MINUTES)
    q = (
        db.query(AlertEvent)
        .filter(AlertEvent.dataset_id == dataset_id)
        .filter(AlertEvent.created_at >= cutoff)
        .filter(AlertEvent.title == "Risk spike detected")
    )
    return db.query(q.exists()).scalar() is True


def _get_latest_signal_timestamp(db: Session, dataset_id):
    from app.models.alert_event import AlertEvent as SignalAlertEvent
    from app.models.dataset_insight import DatasetInsight
    from app.models.ingestion_run import IngestionRun

    latest_run = (
        db.query(IngestionRun.created_at)
        .filter(IngestionRun.dataset_id == dataset_id)
        .order_by(IngestionRun.created_at.desc())
        .limit(1)
        .scalar()
    )

    latest_insight = (
        db.query(DatasetInsight.created_at)
        .filter(DatasetInsight.dataset_id == dataset_id)
        .order_by(DatasetInsight.created_at.desc())
        .limit(1)
        .scalar()
    )

    latest_alert = (
        db.query(SignalAlertEvent.created_at)
        .filter(SignalAlertEvent.dataset_id == dataset_id)
        .order_by(SignalAlertEvent.created_at.desc())
        .limit(1)
        .scalar()
    )

    return max(filter(None, [latest_run, latest_insight, latest_alert]), default=None)


def track_dataset_risk(db: Session, dataset_id) -> Optional[DatasetRiskHistory | dict[str, Any]]:
    res = compute_dataset_risk(db, dataset_id)
    if res is None:
        return None

    current_score = int(res.dataset_risk_score)
    current_level = str(res.risk_level)
    breakdown = res.breakdown

    last = (
        db.query(DatasetRiskHistory)
        .filter(DatasetRiskHistory.dataset_id == dataset_id)
        .order_by(DatasetRiskHistory.created_at.desc())
        .first()
    )

    if last:
        if last.risk_score == current_score and last.risk_level == current_level:
            logger.info(
                "Risk unchanged - skipping history insert",
                extra={"dataset_id": str(dataset_id)},
            )
            return {
                "dataset_id": str(dataset_id),
                "risk_score": current_score,
                "risk_level": current_level,
                "breakdown": breakdown,
                "skipped": True,
            }

    # Fetch previous snapshot BEFORE inserting new one
    prev = last

    # Insert new snapshot
    snap = DatasetRiskHistory(
        dataset_id=dataset_id,
        risk_score=current_score,
        risk_level=current_level,
        breakdown=breakdown,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)

    # --- Risk Spike Detection ---
    if prev is not None:
        delta = int(res.dataset_risk_score) - int(prev.risk_score)

        if delta >= RISK_SPIKE_WARNING_THRESHOLD:
            if not _risk_spike_cooldown_exists(db, dataset_id):
                severity = "warning"
                if delta >= RISK_SPIKE_CRITICAL_THRESHOLD:
                    severity = "critical"

                db.add(
                    AlertEvent(
                        dataset_id=dataset_id,
                        rule_id=None,
                        severity=severity,
                        title="Risk spike detected",
                        message=(
                            f"Risk score increased from {prev.risk_score} "
                            f"to {res.dataset_risk_score} (Δ={delta})."
                        ),
                        payload={
                            "type": "RISK_SPIKE",
                            "previous_score": int(prev.risk_score),
                            "new_score": int(res.dataset_risk_score),
                            "delta": int(delta),
                            "previous_level": prev.risk_level,
                            "new_level": res.risk_level,
                        },
                    )
                )
                db.commit()

    return snap
