from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.dataset import Dataset


def get_owned_dataset(db: Session, dataset_id, user_id) -> Dataset:
    ds = (
        db.query(Dataset)
        .filter(Dataset.id == dataset_id)
        .filter(Dataset.owner_id == user_id)
        .first()
    )
    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )
    return ds
