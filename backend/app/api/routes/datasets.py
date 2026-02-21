from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.dataset import Dataset, DatasetColumn
from app.schemas.dataset import DatasetCreate, DatasetListOut, DatasetOut

logger = logging.getLogger("insightsentinel")

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
def create_dataset(payload: DatasetCreate, db: Session = Depends(get_db)) -> DatasetOut:
    dataset = Dataset(
        name=payload.name,
        description=payload.description,
        row_count=payload.row_count,
        column_count=payload.column_count,
    )

    for col in payload.columns:
        dataset.columns.append(
            DatasetColumn(
                name=col.name,
                dtype=col.dtype,
                null_count=col.null_count,
                distinct_count=col.distinct_count,
            )
        )

    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    logger.info("Created dataset id=%s name=%s", dataset.id, dataset.name)
    return DatasetOut.model_validate(dataset)


@router.get("", response_model=list[DatasetListOut])
def list_datasets(db: Session = Depends(get_db)) -> list[DatasetListOut]:
    rows = db.query(Dataset).order_by(Dataset.created_at.desc()).all()
    return [DatasetListOut.model_validate(r) for r in rows]


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: uuid.UUID, db: Session = Depends(get_db)) -> DatasetOut:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return DatasetOut.model_validate(dataset)