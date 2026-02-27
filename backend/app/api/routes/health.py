from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.dataset_access import get_owned_dataset
from app.services.risk_engine import compute_dataset_health

router = APIRouter(prefix="/datasets", tags=["health"])


@router.get("/{dataset_id}/health")
def get_health(
    dataset_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_dataset(db, dataset_id, current_user.id)
    health = compute_dataset_health(db, dataset_id)
    if health is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return health
