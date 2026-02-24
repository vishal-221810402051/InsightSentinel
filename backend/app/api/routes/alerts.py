from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.alert_event import AlertEvent
from app.models.alert_rule import AlertRule
from app.models.dataset import Dataset
from app.schemas.alerts import AlertEventCreate, AlertEventOut, AlertRuleCreate, AlertRuleOut

router = APIRouter(prefix="/datasets/{dataset_id}/alerts", tags=["alerts"])


def _ensure_dataset(db: Session, dataset_id: UUID) -> Dataset:
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds


@router.post("/rules", response_model=AlertRuleOut)
def create_rule(dataset_id: UUID, payload: AlertRuleCreate, db: Session = Depends(get_db)):
    _ensure_dataset(db, dataset_id)

    rule = AlertRule(
        dataset_id=dataset_id,
        name=payload.name,
        description=payload.description,
        rule_type=payload.rule_type,
        config=payload.config,
        is_enabled=payload.is_enabled,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/rules", response_model=List[AlertRuleOut])
def list_rules(dataset_id: UUID, db: Session = Depends(get_db)):
    _ensure_dataset(db, dataset_id)
    return (
        db.query(AlertRule)
        .filter(AlertRule.dataset_id == dataset_id)
        .order_by(AlertRule.created_at.desc())
        .all()
    )


@router.get("/events", response_model=List[AlertEventOut])
def list_events(dataset_id: UUID, limit: int = 50, db: Session = Depends(get_db)):
    _ensure_dataset(db, dataset_id)
    limit = max(1, min(limit, 500))
    return (
        db.query(AlertEvent)
        .filter(AlertEvent.dataset_id == dataset_id)
        .order_by(AlertEvent.created_at.desc())
        .limit(limit)
        .all()
    )


# Optional but VERY useful for Phase 5A validation:
@router.post("/events", response_model=AlertEventOut)
def create_event(dataset_id: UUID, payload: AlertEventCreate, db: Session = Depends(get_db)):
    _ensure_dataset(db, dataset_id)

    ev = AlertEvent(
        dataset_id=dataset_id,
        rule_id=payload.rule_id,
        severity=payload.severity,
        title=payload.title,
        message=payload.message,
        payload=payload.payload,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev
