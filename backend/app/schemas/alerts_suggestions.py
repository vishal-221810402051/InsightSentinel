from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class AlertRuleSuggestion(BaseModel):
    rule_type: str
    name: str
    description: Optional[str] = None
    config: dict[str, Any] = Field(default_factory=dict)
    severity: str = "info"  # info | warning | critical
    rationale: str


class AlertSuggestionsResponse(BaseModel):
    dataset_id: str
    count: int
    suggestions: list[AlertRuleSuggestion]
