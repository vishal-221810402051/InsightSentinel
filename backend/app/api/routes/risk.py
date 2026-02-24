from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.dataset_risk_history import DatasetRiskHistory
from app.services.risk_engine import compute_dataset_risk, track_dataset_risk

router = APIRouter(prefix="/datasets", tags=["risk"])


@router.get("/{dataset_id}/risk")
def get_dataset_risk(dataset_id: UUID, db: Session = Depends(get_db)):
    res = compute_dataset_risk(db, dataset_id)
    if res is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return {
        "dataset_id": res.dataset_id,
        "dataset_risk_score": res.dataset_risk_score,
        "risk_level": res.risk_level,
        "breakdown": res.breakdown,
        "top_risks": res.top_risks,
    }


@router.post("/{dataset_id}/risk/track")
def track_risk(dataset_id: UUID, db: Session = Depends(get_db)):
    snap = track_dataset_risk(db, dataset_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if isinstance(snap, dict):
        return snap

    return {
        "dataset_id": str(snap.dataset_id),
        "risk_score": snap.risk_score,
        "risk_level": snap.risk_level,
        "breakdown": snap.breakdown,
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
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }
