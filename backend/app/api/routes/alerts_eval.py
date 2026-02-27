from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.alert_engine import evaluate_dataset_rules
from app.services.dataset_access import get_owned_dataset

router = APIRouter(prefix="/datasets", tags=["alerts"])


@router.post("/{dataset_id}/alerts/evaluate")
def evaluate_alerts(
    dataset_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_dataset(db, dataset_id, current_user.id)
    summary = evaluate_dataset_rules(db, dataset_id)
    return {
        "dataset_id": str(dataset_id),
        "created_events": summary.created_events,
        "evaluated_rules": summary.evaluated_rules,
        "skipped_rules": summary.skipped_rules,
        "no_signal_rules": summary.no_signal_rules,
        "unsupported_rules": summary.unsupported_rules,
    }
