from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.dataset_anomaly_event import DatasetAnomalyEvent
from app.models.user import User
from app.services.anomaly_engine import detect_latest_zscore_anomaly
from app.services.dataset_access import get_owned_dataset

router = APIRouter(prefix="/datasets/{dataset_id}/anomalies", tags=["anomalies"])


@router.post("/detect")
def detect_anomaly(
    dataset_id: UUID,
    metric: str = Query(default="risk_score"),
    window: int = Query(default=20, ge=5, le=200),
    z: float = Query(default=3.0, gt=0.0, lt=20.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    get_owned_dataset(db, dataset_id, current_user.id)
    created = detect_latest_zscore_anomaly(
        db, dataset_id, metric=metric, window=window, z_threshold=z
    )
    return {
        "dataset_id": str(dataset_id),
        "metric": metric,
        "window": window,
        "z_threshold": z,
        "created_events": int(created),
    }


@router.get("")
def list_anomalies(
    dataset_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    get_owned_dataset(db, dataset_id, current_user.id)
    rows = (
        db.query(DatasetAnomalyEvent)
        .filter(DatasetAnomalyEvent.dataset_id == dataset_id)
        .order_by(DatasetAnomalyEvent.created_at.desc())
        .limit(limit)
        .all()
    )

    events = [
        {
            "id": str(r.id),
            "dataset_id": str(r.dataset_id),
            "metric": r.metric,
            "value": r.value,
            "rolling_mean": r.rolling_mean,
            "rolling_std": r.rolling_std,
            "z_score": r.z_score,
            "window": r.window,
            "threshold": r.threshold,
            "direction": r.direction,
            "created_at": r.created_at,
        }
        for r in rows
    ]
    return {"dataset_id": str(dataset_id), "count": len(events), "events": events}
