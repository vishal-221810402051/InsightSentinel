from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    rule_type: str = Field(..., min_length=1, max_length=64)
    config: dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True


class AlertRuleOut(BaseModel):
    id: UUID
    dataset_id: UUID
    name: str
    description: Optional[str]
    rule_type: str
    config: dict[str, Any]
    is_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertEventCreate(BaseModel):
    rule_id: Optional[UUID] = None
    severity: str = Field(..., min_length=1, max_length=20)  # info|warning|critical
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=2000)
    payload: Optional[dict[str, Any]] = None


class AlertEventOut(BaseModel):
    id: UUID
    dataset_id: UUID
    rule_id: Optional[UUID]
    severity: str
    title: str
    message: str
    payload: Optional[dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True
