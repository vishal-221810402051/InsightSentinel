from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
from typing import Optional, Tuple

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.dataset_anomaly_event import DatasetAnomalyEvent
from app.models.dataset_risk_history import DatasetRiskHistory

_COOLDOWN_MINUTES = 10


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _cooldown_exists(db: Session, dataset_id, metric: str) -> bool:
    cutoff = _now() - timedelta(minutes=_COOLDOWN_MINUTES)
    q = (
        db.query(DatasetAnomalyEvent)
        .filter(DatasetAnomalyEvent.dataset_id == dataset_id)
        .filter(DatasetAnomalyEvent.metric == metric)
        .filter(DatasetAnomalyEvent.created_at >= cutoff)
    )
    return db.query(q.exists()).scalar() is True


def _rolling_baseline(values: list[float]) -> Tuple[Optional[float], Optional[float]]:
    if not values:
        return None, None

    m = sum(values) / len(values)
    var = sum((x - m) ** 2 for x in values) / len(values)
    s = math.sqrt(var)
    return m, s


def _should_evaluate_latest_point(db: Session, dataset_id, metric: str) -> bool:
    """
    Dedupe gate: only evaluate if there is a new risk_history point
    newer than the last anomaly event for this metric.
    """
    latest_risk = (
        db.query(DatasetRiskHistory)
        .filter(DatasetRiskHistory.dataset_id == dataset_id)
        .order_by(desc(DatasetRiskHistory.created_at))
        .first()
    )
    if not latest_risk:
        return False

    latest_anom = (
        db.query(DatasetAnomalyEvent)
        .filter(DatasetAnomalyEvent.dataset_id == dataset_id)
        .filter(DatasetAnomalyEvent.metric == metric)
        .order_by(desc(DatasetAnomalyEvent.created_at))
        .first()
    )

    # If we never emitted an anomaly before, evaluate.
    if not latest_anom:
        return True

    # Only evaluate if risk point is strictly newer than last anomaly event.
    return latest_risk.created_at > latest_anom.created_at


def detect_latest_zscore_anomaly(
    db: Session,
    dataset_id,
    metric: str = "risk_score",
    window: int = 20,
    z_threshold: float = 3.0,
) -> int:
    """
    Detect anomaly for the latest point using baseline from previous `window` points.
    Persists 0/1 anomaly event.
    """
    try:
        window = int(window)
        z_threshold = float(z_threshold)
        if window < 5 or z_threshold <= 0 or not math.isfinite(z_threshold):
            return 0
        if metric != "risk_score":
            # Keep v1 strict. Later we can add "health_score".
            return 0
        if not _should_evaluate_latest_point(db, dataset_id, metric):
            return 0

        # Need window + 1 points: baseline(window) + latest(1).
        rows = (
            db.query(DatasetRiskHistory)
            .filter(DatasetRiskHistory.dataset_id == dataset_id)
            .order_by(DatasetRiskHistory.created_at.desc())
            .limit(window + 1)
            .all()
        )
        if len(rows) < window + 1:
            return 0

        # Rows are newest-first; reverse for time order.
        rows = list(reversed(rows))
        baseline_rows = rows[:-1]
        latest = rows[-1]

        baseline_vals = [
            float(r.risk_score) for r in baseline_rows if r.risk_score is not None
        ]
        if len(baseline_vals) < window:
            return 0

        mean_v, std_v = _rolling_baseline(baseline_vals)
        if mean_v is None or std_v is None or std_v == 0 or not math.isfinite(std_v):
            return 0

        value = float(latest.risk_score)
        z = (value - mean_v) / std_v
        if not math.isfinite(z):
            return 0

        if abs(z) < z_threshold:
            return 0

        # Cooldown per dataset+metric to avoid spam.
        if _cooldown_exists(db, dataset_id, metric):
            return 0

        direction = "spike" if z > 0 else "drop"
        db.add(
            DatasetAnomalyEvent(
                dataset_id=dataset_id,
                metric=metric,
                value=value,
                rolling_mean=float(mean_v),
                rolling_std=float(std_v),
                z_score=float(z),
                window=window,
                threshold=float(z_threshold),
                direction=direction,
            )
        )
        db.commit()
        return 1
    except Exception:
        # Never crash callers.
        return 0
