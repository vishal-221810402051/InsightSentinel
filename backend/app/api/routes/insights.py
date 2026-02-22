from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Dataset
from app.models.dataset_insight import DatasetInsight
from app.schemas.insight import DatasetInsightsResponseOut
from app.services.insights_engine import refresh_insights

router = APIRouter(prefix="/datasets", tags=["insights"])


@router.get("/{dataset_id}/insights", response_model=DatasetInsightsResponseOut)
def get_dataset_insights(
    dataset_id: uuid.UUID,
    refresh: bool = Query(False, description="Recompute insights before returning"),
    db: Session = Depends(get_db),
):
    dataset_exists = db.query(Dataset.id).filter(Dataset.id == dataset_id).first()
    if not dataset_exists:
        raise HTTPException(status_code=404, detail="Dataset not found")

    items = (
        refresh_insights(db, dataset_id)
        if refresh
        else db.query(DatasetInsight)
        .filter(DatasetInsight.dataset_id == dataset_id)
        .order_by(DatasetInsight.created_at.desc())
        .all()
    )
    return {
        "dataset_id": dataset_id,
        "refreshed": refresh,
        "count": len(items),
        "insights": [
            {
                "dataset_id": r.dataset_id,
                "column_id": r.column_id,
                "severity": r.severity,
                "code": r.code,
                "title": r.title,
                "message": r.message,
                "created_at": r.created_at,
            }
            for r in items
        ],
    }
