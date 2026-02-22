from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models import Dataset, DatasetColumn
from app.models.dataset_preview import DatasetPreview
from app.schemas.dataset import DatasetListOut, DatasetOut
from app.schemas.preview import DatasetPreviewOut

logger = logging.getLogger("insightsentinel")

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetListOut])
def list_datasets(db: Session = Depends(get_db)) -> list[DatasetListOut]:
    rows = db.query(Dataset).order_by(Dataset.created_at.desc()).all()
    return [DatasetListOut.model_validate(r) for r in rows]


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: uuid.UUID, db: Session = Depends(get_db)) -> DatasetOut:
    dataset = (
        db.query(Dataset)
        .options(joinedload(Dataset.columns).joinedload(DatasetColumn.statistics))
        .filter(Dataset.id == dataset_id)
        .first()
    )

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return DatasetOut.model_validate(dataset)


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewOut)
def get_dataset_preview(
    dataset_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> DatasetPreviewOut:
    preview = (
        db.query(DatasetPreview)
        .filter(DatasetPreview.dataset_id == dataset_id)
        .first()
    )

    if not preview:
        raise HTTPException(status_code=404, detail="Preview not found")

    rows = preview.rows or []
    sliced = rows[:limit]

    columns = list(sliced[0].keys()) if sliced else []

    return DatasetPreviewOut(
        dataset_id=dataset_id,
        columns=columns,
        rows=sliced,
        returned_rows=len(sliced),
        stored_rows=len(rows),
    )
