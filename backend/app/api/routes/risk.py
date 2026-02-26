from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.dataset_risk_history import DatasetRiskHistory
from app.services.anomaly_engine import detect_latest_zscore_anomaly
from app.services.risk_engine import compute_dataset_risk, track_dataset_risk

router = APIRouter(prefix="/datasets", tags=["risk"])


@router.get("/{dataset_id}/risk")
def get_dataset_risk(dataset_id: UUID, db: Session = Depends(get_db)):
    res = compute_dataset_risk(db, dataset_id)
    if res is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    latest = (
        db.query(DatasetRiskHistory)
        .filter(DatasetRiskHistory.dataset_id == dataset_id)
        .order_by(desc(DatasetRiskHistory.created_at))
        .first()
    )

    return {
        "dataset_id": res.dataset_id,
        "dataset_risk_score": res.dataset_risk_score,
        "risk_level": res.risk_level,
        "breakdown": res.breakdown,
        "top_risks": res.top_risks,
        "smoothed_score": latest.smoothed_score if latest else None,
        "alpha_used": float(latest.alpha) if latest and latest.alpha is not None else None,
        "delta_score": float(latest.delta_score) if latest and latest.delta_score is not None else None,
        "accel_score": float(latest.accel_score) if latest and latest.accel_score is not None else None,
    }


@router.post("/{dataset_id}/risk/track")
def track_risk(dataset_id: UUID, db: Session = Depends(get_db)):
    snap = track_dataset_risk(db, dataset_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Best-effort anomaly check after risk tracking.
    if not (isinstance(snap, dict) and snap.get("skipped") is True):
        _ = detect_latest_zscore_anomaly(
            db, dataset_id, metric="risk_score", window=20, z_threshold=3.0
        )

    if isinstance(snap, dict):
        return snap

    return {
        "dataset_id": str(snap.dataset_id),
        "risk_score": snap.risk_score,
        "risk_level": snap.risk_level,
        "breakdown": snap.breakdown,
        "smoothed_score": snap.smoothed_score,
        "alpha_used": float(snap.alpha) if snap.alpha is not None else None,
        "delta_score": float(snap.delta_score) if snap.delta_score is not None else None,
        "accel_score": float(snap.accel_score) if snap.accel_score is not None else None,
        "created_at": snap.created_at,
    }


@router.get("/{dataset_id}/risk/history")
def risk_history(dataset_id: UUID, limit: int = 100, db: Session = Depends(get_db)):
    limit = max(1, min(int(limit), 500))

    rows = (
        db.query(DatasetRiskHistory)
        .filter(DatasetRiskHistory.dataset_id == dataset_id)
        .order_by(desc(DatasetRiskHistory.created_at))
        .limit(limit)
        .all()
    )

    return {
        "dataset_id": str(dataset_id),
        "count": len(rows),
        "history": [
            {
                "id": str(r.id),
                "risk_score": r.risk_score,
                "risk_level": r.risk_level,
                "breakdown": r.breakdown,
                "smoothed_score": r.smoothed_score,
                "alpha_used": float(r.alpha) if r.alpha is not None else None,
                "delta_score": float(r.delta_score) if r.delta_score is not None else None,
                "accel_score": float(r.accel_score) if r.accel_score is not None else None,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }
