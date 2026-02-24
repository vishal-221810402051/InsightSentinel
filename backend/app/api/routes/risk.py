from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.risk_engine import compute_dataset_risk

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
