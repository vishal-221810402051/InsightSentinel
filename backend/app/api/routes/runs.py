from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import IngestionRun

router = APIRouter()


@router.get("/{run_id}")
def get_run(run_id: UUID, db: Session = Depends(get_db)) -> dict:
    run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "id": str(run.id),
        "dataset_id": str(run.dataset_id),
        "status": run.status,
        "message": run.message,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "duration_ms": run.duration_ms,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


@router.get("")
def list_runs(
    dataset_id: Optional[UUID] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[dict]:
    q = db.query(IngestionRun)
    if dataset_id:
        q = q.filter(IngestionRun.dataset_id == dataset_id)

    runs = q.order_by(IngestionRun.created_at.desc()).limit(limit).all()

    return [
        {
            "id": str(r.id),
            "dataset_id": str(r.dataset_id),
            "status": r.status,
            "message": r.message,
            "error_message": r.error_message,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "duration_ms": r.duration_ms,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runs
    ]