from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.alerts_suggestions import AlertSuggestionsResponse, AlertRuleSuggestion
from app.services.alert_suggestion_engine import build_alert_suggestions

router = APIRouter(prefix="/datasets", tags=["alerts"])


@router.get("/{dataset_id}/alerts/suggestions", response_model=AlertSuggestionsResponse)
def get_alert_suggestions(
    dataset_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    suggestions = build_alert_suggestions(db, dataset_id, limit=limit)

    out = [
        AlertRuleSuggestion(
            rule_type=s.rule_type,
            name=s.name,
            description=s.description,
            config=s.config,
            severity=s.severity,
            rationale=s.rationale,
        )
        for s in suggestions
    ]

    return AlertSuggestionsResponse(
        dataset_id=str(dataset_id),
        count=len(out),
        suggestions=out,
    )
