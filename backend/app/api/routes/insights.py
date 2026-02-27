from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.dataset_insight import DatasetInsight
from app.models.user import User
from app.schemas.insight import DatasetInsightsResponseOut
from app.services.dataset_access import get_owned_dataset
from app.services.insights_engine import refresh_insights

router = APIRouter(prefix="/datasets", tags=["insights"])


@router.get("/{dataset_id}/insights", response_model=DatasetInsightsResponseOut)
def get_dataset_insights(
    dataset_id: uuid.UUID,
    refresh: bool = Query(False, description="Recompute insights before returning"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_dataset(db, dataset_id, current_user.id)

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
