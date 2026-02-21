from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models import Dataset, DatasetColumn
from app.schemas.dataset import DatasetListOut, DatasetOut

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